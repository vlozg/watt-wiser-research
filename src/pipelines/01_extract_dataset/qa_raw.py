"""Raw-data quality gate: audit raw sources and the landed fnd (qa step between them).

The pipeline is extract (data/raw, verbatim strings on disk) -> quality gate
(this script) -> cast (01_extract_dataset builds typed parquet in data/fnd).
This script never writes data: it reads every raw source as text and the
landed fnd parquets, then writes one JSON report to data/fnd/qa/qa_report.json
and prints a summary. The extractors themselves enforce the casting policy at
build time (measurement junk raises in extract_refit; annotation columns are
dropped and recorded in the manifest in extract_ampds2).

Raw-side checks (string level, per column): numeric parse rate, junk-cell
examples (what errors='coerce' would silently NaN), missing/NULL counts.
Fnd-side checks (per parquet): all-NaN ghost columns, ts_us duplicates,
ts_us non-monotonic runs.

Usage:
  uv run python3 src/pipelines/01_extract_dataset/qa_raw.py             # all datasets
  uv run python3 src/pipelines/01_extract_dataset/qa_raw.py ampds2 redd # subset
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import logging
import os
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import py7zr
import pyarrow.parquet as pq
import tables
from extract_eco import SM_COLS

from wattwiser import FND, RAW, ensure, setup_logging

log = logging.getLogger(__name__)

# rows per read_csv chunk: a string-dtype frame this size stays well under RAM
CHUNK = 1_000_000
ALL = ["ukdale", "ampds2", "redd", "refit", "eco", "greend"]


# report schemas: one dataclass per source shape; record() is the JSON boundary
# (same convention as wattwiser/labels.py: typed commented fields, plain dicts
# only where the JSON is written)


@dataclass
class ColStat:
    """A raw column with non-numeric content (what a coerce would NaN)."""

    junk: int  # non-empty cells failing a numeric parse
    missing: int  # empty cells in the same column
    samples: list[str]  # up to 4 real junk values (dates, flags, text)

    def record(self) -> dict[str, object]:
        return {"junk": self.junk, "missing": self.missing, "samples": self.samples}


@dataclass
class CsvAudit:
    """String-pass result for one CSV source (ukdale, ampds2, refit, eco)."""

    rows: int  # data rows seen
    missing_cells: int  # empty cells across all columns
    junk_cells: int  # total cells a to_numeric coerce would NaN
    ts_col: str | None = None  # ampds2: first col (unix_ts = meter, else annotation)
    non_numeric_cols: dict[str, ColStat] | None = None  # only junk-bearing columns

    def record(self) -> dict[str, object]:
        out: dict[str, object] = {
            "rows": self.rows,
            "missing_cells": self.missing_cells,
            "junk_cells": self.junk_cells,
        }
        if self.ts_col is not None:
            out["ts_col"] = self.ts_col
        if self.non_numeric_cols is not None:
            out["non_numeric_cols"] = {c: s.record() for c, s in self.non_numeric_cols.items()}
        return out


@dataclass
class ReddAudit:
    """REDD pytables measurement table: numeric arrays, so the checks are
    NaN density + ts ordering (no string junk possible)."""

    rows: int  # rows in the table
    missing_cells: int  # NaN cells in the value array
    ts_dups: int  # consecutive duplicate ts_us
    ts_nonmono: int  # consecutive decreasing ts_us

    def record(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "missing_cells": self.missing_cells,
            "ts_dups": self.ts_dups,
            "ts_nonmono": self.ts_nonmono,
        }


@dataclass
class OccupancyAudit:
    """ECO occupancy day-matrix, reported as counts (86,400 value columns)."""

    rows: int  # day rows in the matrix
    missing_cells: int  # == rows: the date col becomes ts, not a value
    junk_cells: int  # non-numeric presence cells (must stay 0)
    date_col_unparseable: int  # rows whose dd-Mon-yyyy date failed to parse

    def record(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "missing_cells": self.missing_cells,
            "junk_cells": self.junk_cells,
            "date_col_unparseable": self.date_col_unparseable,
        }


@dataclass
class GreendColStat:
    """Per-MAC plug column counts for one building."""

    nulls: int  # empty/NULL cells (GREEND's missing marker)
    junk: int  # non-empty cells failing a numeric parse

    def record(self) -> dict[str, object]:
        return {"nulls": self.nulls, "junk": self.junk}


@dataclass
class GreendAudit:
    """Line-level token audit for one GREEND building."""

    data_lines: int  # data lines across all day files
    header_lines: int  # 'timestamp,...' rows (incl. mid-file)
    ts_junk: int  # non-empty ts cells failing float()
    ts_missing: int  # empty ts cells
    degenerate_lines: int  # whitespace-only lines (null-ts rows in fnd)
    ragged_lines: int  # more cells than the block header declares
    junk_samples: list[str]  # example junk ts tokens
    cols: dict[str, GreendColStat]  # only columns with nulls/junk

    def record(self) -> dict[str, object]:
        return {
            "data_lines": self.data_lines,
            "header_lines": self.header_lines,
            "ts_junk": self.ts_junk,
            "ts_missing": self.ts_missing,
            "degenerate_lines": self.degenerate_lines,
            "ragged_lines": self.ragged_lines,
            "junk_samples": self.junk_samples,
            "cols": {c: s.record() for c, s in self.cols.items()},
        }


@dataclass
class FndAudit:
    """One landed fnd parquet: ghost columns + ts_us ordering."""

    rows: int  # parquet rows
    ts_dups: int  # consecutive duplicate ts_us
    ts_nonmono: int  # consecutive decreasing ts_us
    ghost_cols: list[str]  # non-ts columns null in every row

    def record(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "ts_dups": self.ts_dups,
            "ts_nonmono": self.ts_nonmono,
            "ghost_cols": self.ghost_cols,
        }


class ColAudit:
    """Aggregate per-column string stats across files/chunks of one source."""

    def __init__(self) -> None:
        self.rows = 0
        self.missing = 0
        self.stats: dict[str, dict[str, int | set[str]]] = {}

    def feed(self, df: pd.DataFrame) -> None:
        """Classify every cell of one chunk: missing (empty in the source),
        numeric, or junk (non-empty text that to_numeric would coerce to NaN)."""
        self.rows += len(df)
        for c in df.columns:
            s = df[c]
            st = self.stats.setdefault(c, {"missing": 0, "junk": 0, "samples": set()})

            # missing: cell empty in the source (pandas turned it into NaN)
            nn = s.notna()
            self.missing += int((~nn).sum())
            st["missing"] = int(st["missing"]) + int((~nn).sum())

            # junk: non-empty cell failing a numeric parse - exactly the values
            # errors='coerce' would silently turn into NaN downstream
            nonempty = s[nn]
            num = pd.to_numeric(nonempty, errors="coerce")
            bad = nonempty[num.isna()]
            st["junk"] = int(st["junk"]) + int(len(bad))

            # keep a few real examples so the report explains itself
            if len(bad) and len(st["samples"]) < 4:  # type: ignore[operator]
                st["samples"] = set(st["samples"]) | set(bad.astype(str).unique()[:4])  # type: ignore[operator]

    def result(self) -> CsvAudit:
        """Totals always, per-column detail only where junk exists - a clean
        100M-row file stays three numbers in the report."""
        junk = sum(int(v["junk"]) for v in self.stats.values())
        bad_cols = {
            c: ColStat(junk=int(v["junk"]), missing=int(v["missing"]), samples=sorted(v["samples"]))  # type: ignore[arg-type]
            for c, v in self.stats.items()
            if int(v["junk"]) > 0
        }
        return CsvAudit(
            rows=self.rows,
            missing_cells=self.missing,
            junk_cells=junk,
            non_numeric_cols=bad_cols or None,
        )


def audit_csv(
    src: str, sep: str = ",", header: str | int = "infer", names: list[str] | None = None, **kw: object
) -> CsvAudit:
    """Chunked dtype=str pass over one CSV (path or file-like).

    engine='c' is pinned: with a regex sep + dtype=str pandas would otherwise
    fall back to the much slower python engine.
    """
    a = ColAudit()
    for chunk in pd.read_csv(src, sep=sep, header=header, names=names, dtype=str, engine="c", chunksize=CHUNK, **kw):
        a.feed(chunk)
    return a.result()


def qa_ukdale() -> dict[str, CsvAudit]:
    """Audit every house_N/channel_M.dat as raw text (labels.dat is text -> skip)."""
    out: dict[str, CsvAudit] = {}
    root = os.path.join(RAW, "ukdale-full")
    for src in sorted(glob.glob(os.path.join(root, "house_*", "*.dat"))):
        if os.path.basename(src) == "labels.dat":
            continue
        # .dat files are headerless and the column count varies per channel;
        # take the shape from the first data line
        with open(src) as fh:
            ncol = len(fh.readline().split())
        names = ["ts"] + [f"v{i}" for i in range(ncol - 1)]
        key = os.path.relpath(src, root)[:-4]  # remove .dat extension
        out[key] = audit_csv(src, sep=r"\s+", header=None, names=names)
    return out


def qa_ampds2() -> dict[str, CsvAudit]:
    """Audit all AMPds2 CSVs; aux files (billing/climate) are expected to come
    back with text columns, the 30 meter CSVs must be clean."""
    out: dict[str, CsvAudit] = {}
    for src in sorted(glob.glob(os.path.join(RAW, "AMPds2", "*.csv"))):
        r = audit_csv(src)
        # first column name tells meter files (unix_ts) apart from annotation
        # files (a date string), which the extractor drops + records
        with open(src) as fh:
            r.ts_col = fh.readline().split(",")[0]
        out[os.path.basename(src)[:-4]] = r
    return out


def qa_redd() -> dict[str, ReddAudit]:
    """Audit REDD's pytables store: measurement data is numeric arrays, so the
    checks are NaN density + ts ordering (no string junk possible)."""
    out: dict[str, ReddAudit] = {}
    with tables.open_file(os.path.join(RAW, "redd", "redd.h5"), "r") as h:
        for node in h.walk_nodes("/", classname="Table"):
            path = node._v_pathname
            # NILMTK layout: every data node sits at <path>/table (meters +
            # NILMTK's own cache tables - both are audited)
            if not path.endswith("/table"):
                continue
            arr = node.read()
            # index is datetime64[ns] stored as int ns -> // 1000 = us
            ts = arr["index"].astype(np.int64) // 1000
            vals = arr["values_block_0"]
            if vals.ndim == 2:
                vals = vals[:, 0]
            d = np.diff(ts)
            out[path.lstrip("/").replace("/table", "").replace("/", "_")] = ReddAudit(
                rows=int(len(ts)),
                missing_cells=int(pd.isna(vals).sum()),
                ts_dups=int((d == 0).sum()),
                ts_nonmono=int((d < 0).sum()),
            )
    return out


def qa_refit() -> dict[str, CsvAudit]:
    """Audit the 20 CLEAN_HouseN.csv members inside REFIT's .7z archive."""
    out: dict[str, CsvAudit] = {}
    src7z = os.path.join(RAW, "REFIT", "CLEAN_REFIT_081116.7z")
    with py7zr.SevenZipFile(src7z) as z:
        names = [n for n in z.getnames() if n.endswith(".csv")]

    # unpacked each csv one at a time and deleted after the audit
    with tempfile.TemporaryDirectory() as tmp:
        for n in sorted(names):
            with py7zr.SevenZipFile(src7z) as z:
                z.extract(targets=[n], path=tmp)
            src = os.path.join(tmp, n)  # path to the unpacked csv
            out[n[:-4]] = audit_csv(src)  # remove .csv extension
            os.remove(src)  # delete the unpacked csv

    return out


def qa_eco() -> dict[str, CsvAudit | OccupancyAudit]:
    """Audit ECO's three zip families per house: sm (16 named columns),
    plugs (one headerless consumption column per day file), occupancy
    (date + 86,400 binary presence columns, reported as counts only)."""
    out: dict[str, CsvAudit | OccupancyAudit] = {}
    root = os.path.join(RAW, "ECO")
    for zpath in sorted(glob.glob(os.path.join(root, "*_sm_csv.zip"))):
        house = os.path.basename(zpath)[:2]  # extract the house number from the zip path

        # audit the sm zip file, which contains multiple day files
        with zipfile.ZipFile(zpath) as z:
            members = sorted(
                n for n in z.namelist() if n.startswith(house + "/") and n.endswith(".csv") and "__MACOSX" not in n
            )
            # one ColAudit across all day files -> per-house column totals
            a = ColAudit()
            for n in members:
                for chunk in pd.read_csv(io.BytesIO(z.read(n)), header=None, names=SM_COLS, dtype=str, chunksize=CHUNK):
                    a.feed(chunk)
            out[f"house_{house}/sm"] = a.result()

        # audit the plugs zip file
        pz = os.path.join(root, f"{house}_plugs_csv.zip")
        if os.path.exists(pz):
            with zipfile.ZipFile(pz) as z:
                # plug day files are headerless single-column CSVs
                ap = ColAudit()
                for n in sorted(z.namelist()):
                    if not n.endswith(".csv") or "__MACOSX" in n:
                        continue
                    for chunk in pd.read_csv(
                        io.BytesIO(z.read(n)), header=None, names=["consumption"], dtype=str, chunksize=CHUNK
                    ):
                        ap.feed(chunk)
                out[f"house_{house}/plugs"] = ap.result()

        # audit the occupancy zip file
        occ = os.path.join(root, f"{house}_occupancy_csv.zip")
        if os.path.exists(occ):
            with zipfile.ZipFile(occ) as z:
                for season in ("summer", "winter"):
                    member = f"{house}_{season}.csv"
                    if member not in z.namelist():
                        continue
                    # occupancy: 86,401 columns audited individually would bloat
                    # the report, so collapse to per-file counts only
                    df = pd.read_csv(io.BytesIO(z.read(member)), header=None, skiprows=1, dtype=str, chunksize=CHUNK)
                    a = ColAudit()
                    date_bad = 0
                    bad_val = 0
                    rows = 0
                    for chunk in df:
                        rows += len(chunk)
                        # col 0 is a dd-Mon-yyyy date, cols 1.. are 0/1 flags
                        num = pd.to_numeric(chunk[chunk.columns[1:]].stack(), errors="coerce")
                        bad_val += int(num.isna().sum())
                        d = pd.to_datetime(chunk[chunk.columns[0]], format="%d-%b-%Y", errors="coerce")
                        date_bad += int(d.isna().sum())
                    out[f"house_{house}/occupancy_{season}"] = OccupancyAudit(
                        rows=rows,
                        missing_cells=int(rows),
                        junk_cells=int(bad_val),
                        date_col_unparseable=int(date_bad),
                    )
    return out


def qa_greend() -> dict[str, GreendAudit]:
    """Line-level token audit: NULL/empty are by-design nulls, anything else
    that fails float() is a token an error-coerce would silently NaN."""
    src_root = os.path.join(RAW, "GREEND_0-2_300615", "GREEND_0-2_300615")
    out: dict[str, GreendAudit] = {}
    for bdir in sorted(glob.glob(os.path.join(src_root, "building*"))):
        bname = os.path.basename(bdir)
        cols: set[str] = set()
        stat: dict[str, dict[str, int]] = {}
        headers = 0
        ts_junk = ts_missing = degenerate = ragged = rows = 0
        samples: set[str] = set()
        for d in sorted(glob.glob(os.path.join(bdir, "*.csv"))):
            if os.path.getsize(d) < 2:  # zero-byte day file, nothing to audit
                continue

            with open(d) as fh:
                cur: list[str] | None = None  # columns of the current block
                for line in fh:
                    line = line.rstrip("\r\n")
                    if not line:
                        continue
                    if line.startswith("timestamp"):
                        # a header (re)declares the columns for the block below;
                        # buildings re-header mid-file when plugs change
                        cur = line.split(",")[1:]
                        headers += 1
                        for c in cur:
                            if c:
                                cols.add(c)
                        continue
                    if cur is None:
                        continue
                    cells = line.split(",")
                    rows += 1
                    if len(cells) == 1 and not cells[0].strip():
                        # whitespace-only line: fnd keeps it as a null-ts row
                        degenerate += 1
                        continue
                    # ts cell must parse as unix seconds; empty -> missing
                    try:
                        float(cells[0])
                    except ValueError:
                        if cells[0].strip():
                            ts_junk += 1
                            if len(samples) < 4:
                                samples.add(cells[0].strip())
                        else:
                            ts_missing += 1
                    # more cells than the block's header declared = ragged line
                    if len(cells) - 1 > len(cur):
                        ragged += 1
                    # per-MAC plug cell: empty -> null (by design), else numeric
                    for j, cell in enumerate(cells[1:]):
                        st = stat.setdefault(cur[j] if j < len(cur) else "<ragged>", {"nulls": 0, "junk": 0})
                        if not cell.strip():
                            st["nulls"] += 1
                        else:
                            try:
                                float(cell)
                            except ValueError:
                                st["junk"] += 1
        # report only columns that actually have nulls/junk (MAC ids are opaque)
        cols_out = {
            c: GreendColStat(nulls=v["nulls"], junk=v["junk"]) for c, v in stat.items() if v["junk"] or v["nulls"]
        }
        out[bname] = GreendAudit(
            data_lines=rows,
            header_lines=headers,
            ts_junk=ts_junk,
            ts_missing=ts_missing,
            degenerate_lines=degenerate,
            ragged_lines=ragged,
            junk_samples=sorted(samples),
            cols=cols_out,
        )
    return out


def qa_fnd_parquets(ds: str) -> dict[str, FndAudit]:
    """Ghost columns + ts_us dups/non-monotonic runs for every fnd parquet
    (recursive: eco and ukdale store theirs under house_*/ subdirs)."""
    files: dict[str, FndAudit] = {}
    for p in sorted(glob.glob(os.path.join(FND, ds, "**", "*.parquet"), recursive=True)):
        pf = pq.ParquetFile(p)
        names = pf.schema_arrow.names
        rows = pf.metadata.num_rows
        ghosts: list[str] = []
        for ci, c in enumerate(names):
            # skip ts_us column
            if c == "ts_us":
                continue

            nulls = 0
            known = True

            # check if the column is all NULLs
            for rg in range(pf.metadata.num_row_groups):
                st = pf.metadata.row_group(rg).column(ci).statistics
                if st is None or st.null_count is None:
                    known = False
                    break
                nulls += st.null_count

            # if the column is all NULLs, add it to the ghosts list
            if known and nulls == rows:
                ghosts.append(c)

        dups = nonmono = 0

        # check if the ts_us column is monotonic
        prev: int | None = None
        for batch in pf.iter_batches(columns=["ts_us"], batch_size=5_000_000):
            a = batch.column(0).to_numpy(zero_copy_only=False)

            # remove the NA values
            a = a[~pd.isna(a)].astype(np.int64)

            # if the column is empty, continue
            if len(a) == 0:
                continue

            # check if the column has duplicates and is not monotonic
            d = np.diff(a)
            dups += int((d == 0).sum())
            nonmono += int((d < 0).sum())

            if prev is not None:
                dups += int(a[0] == prev)
                nonmono += int(a[0] < prev)
            prev = int(a[-1])

        # keep the file in the report only when there is something to flag
        if ghosts or dups or nonmono:
            # key = path relative to the dataset dir (flat datasets -> bare name)
            files[os.path.relpath(p, os.path.join(FND, ds))] = FndAudit(
                rows=int(rows),
                ts_dups=int(dups),
                ts_nonmono=int(nonmono),
                ghost_cols=ghosts,
            )
    return files


def main() -> None:
    # Parse the command line arguments (datasets to check)
    ap = argparse.ArgumentParser(description="Raw + fnd data-quality gate.")
    ap.add_argument("datasets", nargs="*", help="subset of %s (default: all)" % ALL)
    args = ap.parse_args()
    datasets = args.datasets or ALL
    bad = [d for d in datasets if d not in ALL]
    if bad:
        ap.error("unknown dataset(s): %s" % ", ".join(bad))

    setup_logging()

    t0 = time.time()
    report: dict[str, object] = {"generated_utc": datetime.now(timezone.utc).isoformat(), "raw": {}, "fnd": {}}
    # merge into any existing report so incremental dataset runs compose one file
    path = os.path.join(FND, "qa", "qa_report.json")
    if os.path.exists(path):
        with open(path) as fh:
            report = json.load(fh)
        report["generated_utc"] = datetime.now(timezone.utc).isoformat()

    # Audit the raw data; the audit dataclasses serialize via record() here,
    # the only place the report touches plain dicts
    for ds in datasets:
        log.info(f"qa raw: {ds}")
        raw: dict[str, CsvAudit | ReddAudit | OccupancyAudit | GreendAudit] = {
            "ukdale": qa_ukdale,
            "ampds2": qa_ampds2,
            "redd": qa_redd,
            "refit": qa_refit,
            "eco": qa_eco,
            "greend": qa_greend,
        }[ds]()
        report["raw"][ds] = {k: v.record() for k, v in raw.items()}

    # Audit the fnd parquets
    for ds in datasets:
        log.info(f"qa fnd: {ds}")
        report["fnd"][ds] = {k: v.record() for k, v in qa_fnd_parquets(ds).items()}

    # Write the report
    outdir = os.path.join(FND, "qa")
    ensure(outdir)
    with open(path, "w") as fh:
        json.dump(report, fh, indent=1)

    # Calculate the summary metrics
    raw_junk = sum(
        int(r.get("junk_cells", 0))
        for d in report["raw"].values()  # type: ignore[union-attr]
        for r in d.values()
    )  # type: ignore[union-attr]
    fnd_flagged = sum(len(d) for d in report["fnd"].values())  # type: ignore[union-attr]

    # Log the report path and summary metrics
    log.info(f"report: {path}")
    log.info(f"raw junk cells: {raw_junk}; fnd parquets with findings: {fnd_flagged} ({(time.time() - t0):.0f})")


if __name__ == "__main__":
    main()

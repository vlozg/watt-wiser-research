"""Extract AMPds2 CSVs (electricity channels + aggregate + gas/water/climate) to parquet.

Source: data/raw/AMPds2/{Electricity,NaturalGas,Water,Climate}_*.csv. First column
is unix seconds as stored by the dataset (Burnaby, BC home; semantics preserved).
Non-numeric timestamp columns (Climate) are parsed as datetime; an unparseable
first column (row-label tables) is kept verbatim as a string column beside a
null ts_us. Every other non-numeric column is kept verbatim as a nullable
string and recorded in the manifest (non_numeric_cols) - billing period dates,
ECCC quality flags, weather text and normals extreme-date grids are usable
data. h5/PDF files are not converted. ts_us = unix_seconds * 1e6.

Usage: uv run python3 src/pipelines/01_extract_dataset/extract_ampds2.py [--force]
Writes: data/fnd/ampds2/*.parquet + manifest.json
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import time

import pandas as pd
import tables

from wattwiser import (
    FND,
    RAW,
    done,
    ensure,
    load_manifest,
    record,
    save_manifest,
    setup_logging,
    stat_parquet,
    write_parquet,
)
from wattwiser.labels import Ampds2Building, Ampds2MeterLabel, canonical_label, h5_metadata, write_slice

log = logging.getLogger(__name__)


def extract(force: bool = False) -> None:
    """Convert every AMPds2 CSV to one parquet (resumable via the manifest)."""
    name = "ampds2"
    notes = [
        "source: data/raw/AMPds2/*.csv (Electricity/NaturalGas/Water/Climate); first col = unix seconds as stored",
        "ts_us = unix_seconds * 1e6; numeric columns verbatim; non-numeric columns kept "
        "verbatim as nullable strings (per-file non_numeric_cols records); h5/PDFs not converted",
        "Climate CSVs use datetime strings or unparseable first cols - see per-file note field",
        "registers Pt/Qt/St are corrupt: a one-minute register wipe (2012-05-04) "
        "and a 39-min register meltdown (2013-06-17) make the naive sum of positive "
        "register diffs 3.1x true energy - integrate column P instead of diffing registers",
        "f/DPF/APF are sentinel- or default-filled while a circuit idles (f=0 Hz; "
        "DPF 1.000 or 0.00) - trust V/I/P/Q/S only while the circuit draws (P > 0); "
        "the wide P/Q/S/I files also carry MHE and UNE, computed columns, not meters "
        "(UNE = WHE - RSE - GRE - 18 named, exact in P and S, violates S >= P on 99.3% of minutes)",
        "per-circuit I is the sum of both split-phase legs while V is leg-to-neutral, "
        "so V*I is 2x apparent power on ~240 V circuits (median V*I/S 1.96-2.08) - "
        "use column S, never derive apparent power as V*I",
    ]
    man = load_manifest(name, notes)
    outdir = os.path.join(FND, name)
    ensure(outdir)
    for src in sorted(glob.glob(os.path.join(RAW, "AMPds2", "*.csv"))):
        base = os.path.basename(src)[:-4]
        if not force and done(man, base):
            log.info(f"{base} already processed, skipping")
            continue

        log.info(f"Processing {src}")
        t0 = time.time()
        df = pd.read_csv(src)

        # Parse the timestamp column
        first = df.columns[0]
        ts_raw = df.pop(first)
        num = pd.to_numeric(ts_raw, errors="coerce")
        note = ""
        # decision tree per file, three shapes exist in AMPds2:
        if num.notna().mean() > 0.999 and num.abs().median() > 1e8:
            # meter/climate files: first col is unix seconds -> int64 ts_us
            ts_us = (num * 1e6).astype("int64")
        else:
            dt = pd.to_datetime(ts_raw, errors="coerce")
            if dt.notna().mean() > 0.999:
                # climate files with datetime strings -> parse then to us
                ts_us = dt.astype("int64") // 1000
                note = "first col %r parsed as datetime -> ts_us" % first
            else:
                # row-label tables (Item/Day): the first column is the table's
                # row identity, not a time axis - keep it verbatim as a string
                # column beside a null ts_us instead of discarding it
                ts_us = ((num * 1e6).round()).astype("Int64")
                df.insert(0, first, ts_raw.astype("string"))
                note = "first col %r unparseable; ts_us null, column kept as string" % first
        df.insert(0, "ts_us", ts_us)

        # measurement columns: fully-numeric string columns are recovered as
        # numeric; anything with non-numeric content is kept verbatim as a
        # nullable string (billing periods, ECCC quality flags, weather text,
        # normals extreme-date grids). Dropping would lose usable metadata,
        # NaNifying cells would corrupt mostly-numeric columns; every kept
        # column is recorded in the manifest so the cast stays auditable
        nonnum: dict[str, dict[str, int]] = {}
        for c in list(df.columns):
            if pd.api.types.is_numeric_dtype(df[c]):
                continue
            parsed = pd.to_numeric(df[c], errors="coerce")
            nbad = int((parsed.isna() & df[c].notna()).sum())
            if nbad:
                df[c] = df[c].astype("string")
                nonnum.setdefault(c, {"cells": nbad})
            else:
                df[c] = parsed
        if nonnum:
            log.info(f"{base}: kept {len(nonnum)} non-numeric column(s) as strings: {sorted(nonnum)}")

        # Write the parquet file and record the metadata
        out = os.path.join(outdir, base + ".parquet")
        write_parquet(df, out)
        st = stat_parquet(out)
        if st.rows != len(df):
            raise RuntimeError(f"row mismatch {base}")
        # manifest records which columns are non-numeric strings so the cast step is auditable
        extra: dict[str, dict[str, dict[str, int]]] = {"non_numeric_cols": nonnum} if nonnum else {}
        record(man, name, base, out, src, st, t0, src_cols=first, note=note, src_bytes=os.path.getsize(src), **extra)
        log.info(f"{base}: {len(df)} rows x {df.shape[1]} cols ({(time.time() - t0):.0f}) {note}")

    # persist even when every file was skipped (resume), so notes edits propagate
    save_manifest(name, man)


def extract_labels() -> dict[str, Ampds2Building]:
    """Meter labels from the NILMTK building1 metadata (abbrev names + descriptions)."""
    src = "data/raw/AMPds2/AMPds2.h5"
    with tables.open_file(os.path.join(RAW, "AMPds2", "AMPds2.h5"), "r") as h:
        md = h5_metadata(h.get_node("/building1"))
    site = [k for k, v in md.get("elec_meters", {}).items() if v.get("site_meter")]
    meters: dict[str, list[Ampds2MeterLabel]] = {}
    for a in md.get("appliances", []):
        # AMPds2 stores abbreviations (CWE/DWE/FGE) as original_name; the human
        # name lives in 'description' (type is just 'unknown'/'light'/'sockets')
        label = str(a.get("original_name") or a.get("type"))
        canon = canonical_label(label + " " + str(a.get("description") or ""))
        for m in a.get("meters") or []:
            meters.setdefault(str(m), []).append(
                Ampds2MeterLabel(
                    label=label,
                    canonical=canon,
                    type=a.get("type"),
                    description=a.get("description"),
                    room=a.get("room"),
                )
            )
    return {"building_1": Ampds2Building(source=src, site_meters=site, meters=meters)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--labels", action="store_true", help="extract appliance labels only -> data/gold/appliance_map_ampds2.json"
    )
    a = ap.parse_args()
    setup_logging()
    if a.labels:
        log.info("=== ampds2 labels ===")
        log.info("wrote %s" % write_slice("ampds2", extract_labels()))
        log.info("=== done ampds2 labels ===")
    else:
        log.info("=== ampds2 extract ===")
        extract(force=a.force)
        log.info("=== done ampds2 ===")

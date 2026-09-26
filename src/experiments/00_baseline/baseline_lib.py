"""marimo presentation glue for the experiment notebooks.

The data readers and analysis primitives live in the wattwiser.experiments
package (data_loader, segmentation, energy, evaluation, units); notebooks,
fhmm_lib, and the pipeline scripts import those modules directly. This
module keeps only md_table, the minimal markdown table renderer for mo.md
cells.
"""


def md_table(headers: list[str], rows: list[list]) -> str:
    """Minimal markdown table renderer for mo.md cells."""
    head = "| " + " | ".join(str(h) for h in headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "\n".join([head, sep, body])

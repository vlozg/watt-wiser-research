"""wattwiser.experiments - the power-data steps, one job each.

Every module does one thing and declares the types it exchanges. Read them in
this order and the project reads top to bottom:

    units.py          the unit system (microseconds, watts) and its types
    data_loader.py    every read of the curated tree (parquet + labels)
    segmentation.py   a power series -> ON/OFF episodes, by threshold
    energy.py         energy bookkeeping (Wh per step, window sums, holds)
    evaluation.py     scores a model: episode matching, P/R/F1, timing,
                      per-device error, energy balance
    dataset.py        one house as a task: series, device rules, split,
                      labels - the only place a file becomes a series
    transformations/  pure steps over series and intervals: background,
                      resample, press
    models/           the models: fhmm/ and the anchor baseline

Who may import what: a model imports nothing from this package; a
transformation imports only its own types; dataset.py imports data_loader
and the primitives; the primitives import only units. The pipeline itself -
load a house, estimate the background, draw calibration sessions, fit, decode,
score - lives in the notebook, not in a library function.
"""

"""The pure steps between a raw house and a model input.

Each module turns one kind of thing into another, and does not care who calls
it or what a model is:

    background.py  aggregate series -> floor level + noise around it
    resample.py    native series <-> bucket grid, and cadence rescaling
    press.py       cycle intervals -> calibration sessions (overlap, draws)

Everything here takes plain arrays in and gives plain arrays (or a small
record) back, declaring its own types in types.py, so no module here imports
the dataset or the models. Import the specific module.
"""

"""The models: each one stands on its own and takes plain numbers in and out.

    fhmm/        the learned model: the aggregate is a sum of ON/OFF devices
    anchor.py    the baseline: switch a device on when the meter goes above a
                 limit (arm A0)
    segments.py  the small run/merge helpers both of them use

A model here is handed aligned arrays (times, watts, a few fixed numbers) and
gives plain numbers back (ON flags, probabilities, watts, episodes). Turning a
house into those numbers, and turning the answer into episodes, metrics and
figures, is the caller's job - the notebook or script - so the high-level
pipeline stays readable.

No model imports the dataset, transformation or primitive modules: each
declares the types it expects (models/fhmm/types.py), so a model can be read
and moved on its own.
"""

"""PREPROCESS - sharpness scoring, best-frame selection, depth-to-RGB registration.

The implementation lives in the shared `woundlib` package (pipeline-deps Lambda layer).
"""

from woundlib import steps


def handler(event, context):
    return steps.run_handler(steps.preprocess, event)

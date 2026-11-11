"""GENERATE_DIAGRAMS - top-view SVG and cross-section PNG.

The implementation lives in the shared `woundlib` package (pipeline-deps Lambda layer).
"""

from woundlib import steps


def handler(event, context):
    return steps.run_handler(steps.generate_diagrams, event)

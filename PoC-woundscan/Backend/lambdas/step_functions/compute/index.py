"""COMPUTE - 3D projection, reference-plane fit, L/W/area/depth/peri-wound area -> measurements.json.

The implementation lives in the shared `woundlib` package (pipeline-deps Lambda layer).
"""

from woundlib import steps


def handler(event, context):
    return steps.run_handler(steps.compute, event)

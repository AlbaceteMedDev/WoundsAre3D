"""SEGMENT - SAM ViT-B (SageMaker Serverless, centre-point prompt) wound mask + 20 mm peri-wound ring mask.

The implementation lives in the shared `woundlib` package (pipeline-deps Lambda layer).
"""

from woundlib import steps


def handler(event, context):
    return steps.run_handler(steps.segment, event)

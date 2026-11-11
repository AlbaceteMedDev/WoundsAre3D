"""NARRATE - Bedrock plain-language narration with guardrail on the output.

The implementation lives in the shared `woundlib` package (pipeline-deps Lambda layer).
"""

from woundlib import steps


def handler(event, context):
    return steps.run_handler(steps.narrate, event)

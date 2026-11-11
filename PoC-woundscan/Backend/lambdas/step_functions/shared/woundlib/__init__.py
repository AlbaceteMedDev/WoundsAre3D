"""Shared code for the five wound-scan Step Functions Lambdas.

Packaged into the `pipeline-deps` Lambda layer together with numpy and Pillow,
so every step function can `import woundlib`.
"""

__version__ = "1.0.0"

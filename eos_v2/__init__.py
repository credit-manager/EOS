"""EOS DBP v2 application package.

The v2 runtime is intentionally isolated from the legacy runtime. Migration is
performed by bounded vertical slices; main remains the rollback baseline until
all v2 release gates are green.
"""

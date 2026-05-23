# Tech Debt Tracker

There are no open publish blockers in the current product contract.

## Residual Engineering Debt

- `server.py` is still the primary runtime assembly point
- some internal non-public wrappers remain in dispatcher code for possible future reintroduction
- live test runs can still emit occasional socket-level `ResourceWarning` noise on Windows
- GitHub Actions runs non-live contract tests by default; live validation remains an explicit manual workflow

## Rule For Future Changes

If a removed capability is brought back into the manifests, it must land with support-matrix evidence and contract coverage in the same slice.

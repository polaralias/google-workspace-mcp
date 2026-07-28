---
type: "Delivery Plan"
title: "Tech Debt Tracker"
description: "Documents Tech Debt Tracker for the google-workspace-mcp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - google-workspace-mcp
  - delivery-plan
navigation:
  role: supporting
  order: 100
---
# Tech Debt Tracker

There are no open publish blockers in the current product contract.

## Residual Engineering Debt

- `server.py` is still the primary runtime assembly point
- some internal non-public wrappers remain in dispatcher code for possible future reintroduction
- live test runs can still emit occasional socket-level `ResourceWarning` noise on Windows
- GitHub Actions runs non-live contract tests by default; live validation remains an explicit manual workflow

## Rule For Future Changes

If a removed capability is brought back into the manifests, it must land with support-matrix evidence and contract coverage in the same slice.

## Repository knowledge

- [Documentation map](../knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.

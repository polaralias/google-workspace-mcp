---
type: "Glossary Concept"
title: "Glossary"
description: "Documents Glossary for the google-workspace-mcp repository."
timestamp: 2026-07-28T21:55:36Z
authority: canonical
verification: untested
owner: polaralias
tags:
  - google-workspace-mcp
  - glossary-concept
navigation:
  role: foundational
  order: 20
---
# Glossary

This glossary defines the product-language for the verified public contract of `google-workspace-mcp`.

It is review-derived from the current repository docs and harness surface so future agents have a durable domain-language starting point even where an earlier glossary pass is not evident in tracked history.

## Language

**Product Family**:
A user-meaningful group of related Google Workspace or Google Keep tools that shares one support claim and auth story in the verified support matrix.
_Avoid_: Random tool bucket, implementation module

**Verified Support Matrix**:
The canonical current-state contract that defines which public tool families are supported, by which auth mode, and with what evidence.
_Avoid_: Generated inventory, manifest alone, aspirational roadmap

**Per-Tool Support Matrix**:
The derived companion view that expands the public contract from family level to individual tools.
_Avoid_: Primary support contract, source of truth

**Public Tool Surface**:
The set of tools declared in the public manifests and intentionally exposed by the server.
_Avoid_: Internal dispatcher surface, latent code path

**Supported Runtime Path**:
The execution path the repository is willing to document and support for contributors and operators.
_Avoid_: Any path that happens to boot locally

**Public Manifest**:
A manifest file that defines part of the intentionally exposed interface surface.
_Avoid_: Private registry, internal implementation list

**Verified Working**:
A support label meaning the documented success path is validated to the repository's current evidence bar.
_Avoid_: Probably fine, declared only

**Verified Limited**:
A support label meaning the tool or family is intentionally supported only within a narrow documented boundary that must not be generalised.
_Avoid_: Mostly supported, unofficially broader

**Auth Story**:
The specific supported authentication path required for a product family or workflow.
_Avoid_: Any credentials that happen to work

**Publish Contract**:
The combined public promise about supported runtime path, auth modes, and verified tool surface.
_Avoid_: Internal aspiration, implementation convenience

**Stored OAuth**:
The primary Google Workspace auth story based on persisted user credentials loaded from the configured credentials directory.
_Avoid_: Generic Google auth, API key mode

**API-Key Public Read**:
The narrow compatibility auth story for documented public-read-only tool families.
_Avoid_: General Workspace access

**Keep Master Token**:
The only supported auth story for Google Keep in this repository, based on `GOOGLE_KEEP_EMAIL` plus `GOOGLE_KEEP_MASTER_TOKEN`.
_Avoid_: OAuth Keep support, interchangeable Google auth

**Manifest Presence**:
The fact that a tool is declared in a public manifest and therefore part of the interface surface, but not proof of behaviour by itself.
_Avoid_: Validation, support evidence

**Internal Runtime Code**:
Non-public implementation code that may still exist in the server but does not widen the public contract by itself.
_Avoid_: Supported tool surface

**Opt-In Live Validation**:
Integration coverage that is intentionally gated behind environment setup and is used to prove live external behaviour without becoming the default local test path.
_Avoid_: Always-on baseline tests

## Relationships

- The **Verified Support Matrix** is the canonical contract for current public support
- The **Per-Tool Support Matrix** is subordinate to the **Verified Support Matrix**
- The **Public Tool Surface** is defined by the public manifests
- A **Public Manifest** contributes to the **Public Tool Surface**
- **Manifest Presence** makes a tool part of the **Public Tool Surface** but does not prove **Verified Working**
- The **Publish Contract** combines the **Supported Runtime Path**, auth boundaries, and the **Verified Support Matrix**
- Every **Product Family** has one documented **Auth Story**
- **Stored OAuth** is the primary **Auth Story** for most Google Workspace families
- **API-Key Public Read** is intentionally narrower than **Stored OAuth**
- **Keep Master Token** applies only to Google Keep families
- **Opt-In Live Validation** is evidence for public support, not the default contributor entrypoint
- **Internal Runtime Code** may exist without becoming part of the **Publish Contract**
- A **Verified Limited** claim must document the exact boundary rather than implying broader support

## Example dialogue

> **Dev:** "If a tool is still in the manifest, can we say it is supported?"
> **Domain expert:** "No. **Manifest Presence** defines interface surface, but support claims come from the **Verified Support Matrix**."

## Flagged ambiguities

- "supported" could be inferred from manifest membership alone — resolved: **Manifest Presence** is interface declaration, not proof
- generated per-tool docs could be mistaken for the main contract — resolved: the **Verified Support Matrix** is canonical and the **Per-Tool Support Matrix** is derived
- local boot success could be mistaken for the supported operator path — resolved: the **Supported Runtime Path** is what the docs explicitly support
- API-key availability could be read as broad Google Workspace support — resolved: **API-Key Public Read** is a narrow compatibility story only
- Google Keep auth could be conflated with Workspace OAuth — resolved: **Keep Master Token** is a distinct auth story with its own boundary
- internal code presence could be mistaken for public commitment — resolved: **Internal Runtime Code** does not widen the **Publish Contract**
- live test coverage could be mistaken for the default local harness — resolved: **Opt-In Live Validation** is gated proof, not the baseline path
- family-level support and tool-level support could blur together — resolved: **Product Family** is the contract centre, with tool-level expansion kept subordinate

## Repository knowledge

- [Documentation map](docs/knowledge/documentation-map.md) — RKE-managed reading order and relationship hub.

# google-workspace-mcp

> Generated from repository-local OKF records. The Markdown/YAML bundle remains canonical.

Source: `google-workspace-mcp`

The report separates the connected repository map from detailed component and key-concept views so large bundles remain reviewable.

## Connected-area overview

```mermaid
flowchart LR
    a0["docs · 14 concepts"]
    a1["repository root · 3 concepts"]
    a2["tasks · 1 concepts"]
    a0 -->|links| a1
    a0 -->|links| a2
    a1 -->|links| a0
    a2 -->|links| a0
    classDef default fill:#eef2ff,stroke:#4f46e5,color:#1e1b4b
```

## Connected component 1

```mermaid
flowchart LR
    n0["Architecture"]:::knowledge
    n1["Configuration Reference"]:::knowledge
    n2["Core Beliefs"]:::knowledge
    n3["Tech Debt Tracker"]:::knowledge
    n4["google-workspace-mcp complete Markdown inventory"]:::knowledge
    n5["google-workspace-mcp documentation map"]:::knowledge
    n6["google-workspace-mcp repository OKF visualization"]:::knowledge
    n7["Plans"]:::knowledge
    n8["Auth Models"]:::knowledge
    n9["Product And Platform End State"]:::knowledge
    n10["Verified Support Matrix"]:::knowledge
    n11["Reliability"]:::knowledge
    n12["Security"]:::knowledge
    n13["Tool Reference"]:::knowledge
    n14["Validation Report - 2026-05-16"]:::knowledge
    n15["Glossary"]:::knowledge
    n16["Google Workspace MCP"]:::knowledge
    n17["Adopt RKE OKF knowledge format · done"]:::task
    n0 -->|links| n16
    n0 -->|links| n1
    n0 -->|links| n10
    n0 -->|links| n8
    n0 -->|links| n11
    n0 -->|links| n5
    n1 -->|links| n5
    n2 -->|links| n5
    n3 -->|links| n5
    n4 -->|links| n0
    n4 -->|links| n1
    n4 -->|links| n2
    n4 -->|links| n3
    n4 -->|links| n5
    n4 -->|links| n6
    n4 -->|links| n7
    n4 -->|links| n8
    n4 -->|links| n9
    n4 -->|links| n10
    n4 -->|links| n11
    n4 -->|links| n12
    n4 -->|links| n13
    n4 -->|links| n14
    n4 -->|links| n15
    n4 -->|links| n16
    n4 -->|links| n17
    n5 -->|links| n16
    n5 -->|links| n4
    n5 -->|links| n0
    n5 -->|links| n3
    n5 -->|links| n7
    n5 -->|links| n2
    n5 -->|links| n15
    n5 -->|links| n8
    n5 -->|links| n9
    n5 -->|links| n10
    n5 -->|links| n1
    n5 -->|links| n13
    n5 -->|links| n11
    n5 -->|links| n12
    n5 -->|links| n14
    n5 -->|links| n17
    n5 -->|links| n6
    n6 -->|links| n5
    n6 -->|links| n4
    n6 -->|links| n17
    n7 -->|links| n5
    n8 -->|links| n5
    n9 -->|links| n5
    n10 -->|links| n5
    n11 -->|links| n5
    n12 -->|links| n5
    n13 -->|links| n5
    n14 -->|links| n5
    n15 -->|links| n5
    n16 -->|links| n1
    n16 -->|links| n13
    n16 -->|links| n10
    n16 -->|links| n5
    n17 -->|links| n5
    n17 -->|links| n6
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

## Key concept neighbourhoods

### google-workspace-mcp documentation map

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Configuration Reference"]:::boundary
    n2["Core Beliefs"]:::boundary
    n3["Tech Debt Tracker"]:::boundary
    n4["google-workspace-mcp complete Markdown inventory"]:::boundary
    n5["google-workspace-mcp documentation map"]:::knowledge
    n6["google-workspace-mcp repository OKF visualization"]:::boundary
    n7["Plans"]:::boundary
    n8["Auth Models"]:::boundary
    n9["Product And Platform End State"]:::boundary
    n10["Verified Support Matrix"]:::boundary
    n11["Reliability"]:::boundary
    n12["Security"]:::boundary
    n13["Tool Reference"]:::boundary
    n14["Validation Report - 2026-05-16"]:::boundary
    n15["Glossary"]:::boundary
    n16["Google Workspace MCP"]:::boundary
    n17["Adopt RKE OKF knowledge format · done"]:::boundary
    n0 -->|links| n16
    n0 -->|links| n1
    n0 -->|links| n10
    n0 -->|links| n8
    n0 -->|links| n11
    n0 -->|links| n5
    n1 -->|links| n5
    n2 -->|links| n5
    n3 -->|links| n5
    n4 -->|links| n0
    n4 -->|links| n1
    n4 -->|links| n2
    n4 -->|links| n3
    n4 -->|links| n5
    n4 -->|links| n6
    n4 -->|links| n7
    n4 -->|links| n8
    n4 -->|links| n9
    n4 -->|links| n10
    n4 -->|links| n11
    n4 -->|links| n12
    n4 -->|links| n13
    n4 -->|links| n14
    n4 -->|links| n15
    n4 -->|links| n16
    n4 -->|links| n17
    n5 -->|links| n16
    n5 -->|links| n4
    n5 -->|links| n0
    n5 -->|links| n3
    n5 -->|links| n7
    n5 -->|links| n2
    n5 -->|links| n15
    n5 -->|links| n8
    n5 -->|links| n9
    n5 -->|links| n10
    n5 -->|links| n1
    n5 -->|links| n13
    n5 -->|links| n11
    n5 -->|links| n12
    n5 -->|links| n14
    n5 -->|links| n17
    n5 -->|links| n6
    n6 -->|links| n5
    n6 -->|links| n4
    n6 -->|links| n17
    n7 -->|links| n5
    n8 -->|links| n5
    n9 -->|links| n5
    n10 -->|links| n5
    n11 -->|links| n5
    n12 -->|links| n5
    n13 -->|links| n5
    n14 -->|links| n5
    n15 -->|links| n5
    n16 -->|links| n1
    n16 -->|links| n13
    n16 -->|links| n10
    n16 -->|links| n5
    n17 -->|links| n5
    n17 -->|links| n6
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### google-workspace-mcp complete Markdown inventory

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Configuration Reference"]:::boundary
    n2["Core Beliefs"]:::boundary
    n3["Tech Debt Tracker"]:::boundary
    n4["google-workspace-mcp complete Markdown inventory"]:::knowledge
    n5["google-workspace-mcp documentation map"]:::boundary
    n6["google-workspace-mcp repository OKF visualization"]:::boundary
    n7["Plans"]:::boundary
    n8["Auth Models"]:::boundary
    n9["Product And Platform End State"]:::boundary
    n10["Verified Support Matrix"]:::boundary
    n11["Reliability"]:::boundary
    n12["Security"]:::boundary
    n13["Tool Reference"]:::boundary
    n14["Validation Report - 2026-05-16"]:::boundary
    n15["Glossary"]:::boundary
    n16["Google Workspace MCP"]:::boundary
    n17["Adopt RKE OKF knowledge format · done"]:::boundary
    n0 -->|links| n16
    n0 -->|links| n1
    n0 -->|links| n10
    n0 -->|links| n8
    n0 -->|links| n11
    n0 -->|links| n5
    n1 -->|links| n5
    n2 -->|links| n5
    n3 -->|links| n5
    n4 -->|links| n0
    n4 -->|links| n1
    n4 -->|links| n2
    n4 -->|links| n3
    n4 -->|links| n5
    n4 -->|links| n6
    n4 -->|links| n7
    n4 -->|links| n8
    n4 -->|links| n9
    n4 -->|links| n10
    n4 -->|links| n11
    n4 -->|links| n12
    n4 -->|links| n13
    n4 -->|links| n14
    n4 -->|links| n15
    n4 -->|links| n16
    n4 -->|links| n17
    n5 -->|links| n16
    n5 -->|links| n4
    n5 -->|links| n0
    n5 -->|links| n3
    n5 -->|links| n7
    n5 -->|links| n2
    n5 -->|links| n15
    n5 -->|links| n8
    n5 -->|links| n9
    n5 -->|links| n10
    n5 -->|links| n1
    n5 -->|links| n13
    n5 -->|links| n11
    n5 -->|links| n12
    n5 -->|links| n14
    n5 -->|links| n17
    n5 -->|links| n6
    n6 -->|links| n5
    n6 -->|links| n4
    n6 -->|links| n17
    n7 -->|links| n5
    n8 -->|links| n5
    n9 -->|links| n5
    n10 -->|links| n5
    n11 -->|links| n5
    n12 -->|links| n5
    n13 -->|links| n5
    n14 -->|links| n5
    n15 -->|links| n5
    n16 -->|links| n1
    n16 -->|links| n13
    n16 -->|links| n10
    n16 -->|links| n5
    n17 -->|links| n5
    n17 -->|links| n6
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### Architecture

```mermaid
flowchart LR
    n0["Architecture"]:::knowledge
    n1["Configuration Reference"]:::boundary
    n2["google-workspace-mcp complete Markdown inventory"]:::boundary
    n3["google-workspace-mcp documentation map"]:::boundary
    n4["Auth Models"]:::boundary
    n5["Verified Support Matrix"]:::boundary
    n6["Reliability"]:::boundary
    n7["Google Workspace MCP"]:::boundary
    n0 -->|links| n7
    n0 -->|links| n1
    n0 -->|links| n5
    n0 -->|links| n4
    n0 -->|links| n6
    n0 -->|links| n3
    n1 -->|links| n3
    n2 -->|links| n0
    n2 -->|links| n1
    n2 -->|links| n3
    n2 -->|links| n4
    n2 -->|links| n5
    n2 -->|links| n6
    n2 -->|links| n7
    n3 -->|links| n7
    n3 -->|links| n2
    n3 -->|links| n0
    n3 -->|links| n4
    n3 -->|links| n5
    n3 -->|links| n1
    n3 -->|links| n6
    n4 -->|links| n3
    n5 -->|links| n3
    n6 -->|links| n3
    n7 -->|links| n1
    n7 -->|links| n5
    n7 -->|links| n3
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### Google Workspace MCP

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Configuration Reference"]:::boundary
    n2["google-workspace-mcp complete Markdown inventory"]:::boundary
    n3["google-workspace-mcp documentation map"]:::boundary
    n4["Verified Support Matrix"]:::boundary
    n5["Tool Reference"]:::boundary
    n6["Google Workspace MCP"]:::knowledge
    n0 -->|links| n6
    n0 -->|links| n1
    n0 -->|links| n4
    n0 -->|links| n3
    n1 -->|links| n3
    n2 -->|links| n0
    n2 -->|links| n1
    n2 -->|links| n3
    n2 -->|links| n4
    n2 -->|links| n5
    n2 -->|links| n6
    n3 -->|links| n6
    n3 -->|links| n2
    n3 -->|links| n0
    n3 -->|links| n4
    n3 -->|links| n1
    n3 -->|links| n5
    n4 -->|links| n3
    n5 -->|links| n3
    n6 -->|links| n1
    n6 -->|links| n5
    n6 -->|links| n4
    n6 -->|links| n3
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### google-workspace-mcp repository OKF visualization

```mermaid
flowchart LR
    n0["google-workspace-mcp complete Markdown inventory"]:::boundary
    n1["google-workspace-mcp documentation map"]:::boundary
    n2["google-workspace-mcp repository OKF visualization"]:::knowledge
    n3["Adopt RKE OKF knowledge format · done"]:::boundary
    n0 -->|links| n1
    n0 -->|links| n2
    n0 -->|links| n3
    n1 -->|links| n0
    n1 -->|links| n3
    n1 -->|links| n2
    n2 -->|links| n1
    n2 -->|links| n0
    n2 -->|links| n3
    n3 -->|links| n1
    n3 -->|links| n2
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

### Configuration Reference

```mermaid
flowchart LR
    n0["Architecture"]:::boundary
    n1["Configuration Reference"]:::knowledge
    n2["google-workspace-mcp complete Markdown inventory"]:::boundary
    n3["google-workspace-mcp documentation map"]:::boundary
    n4["Google Workspace MCP"]:::boundary
    n0 -->|links| n4
    n0 -->|links| n1
    n0 -->|links| n3
    n1 -->|links| n3
    n2 -->|links| n0
    n2 -->|links| n1
    n2 -->|links| n3
    n2 -->|links| n4
    n3 -->|links| n4
    n3 -->|links| n2
    n3 -->|links| n0
    n3 -->|links| n1
    n4 -->|links| n1
    n4 -->|links| n3
    classDef task fill:#dbeafe,stroke:#2563eb,color:#172554
    classDef workstream fill:#ede9fe,stroke:#7c3aed,color:#2e1065
    classDef tracker fill:#ffedd5,stroke:#ea580c,color:#431407
    classDef knowledge fill:#dcfce7,stroke:#16a34a,color:#052e16
    classDef boundary fill:#f8fafc,stroke:#64748b,color:#0f172a,stroke-dasharray:4 3
```

## Legend

- Blue: task
- Purple: workstream
- Orange: tracker profile
- Green: durable knowledge
- Dashed neutral nodes: neighbouring context repeated from another area or key-concept view
- Time references: edges to addressable `Task.time[]` fragments
- Arrows: structured relationships or repository-local Markdown links

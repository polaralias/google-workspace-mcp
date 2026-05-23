# Core Beliefs

## Belief 1: Declared support is not enough

A manifest entry is not proof of capability. Public claims should follow verification.

## Belief 2: Auth stories must be explicit

Stored OAuth is the primary supported Workspace auth story. API key and Keep master token are narrower compatibility stories. Unsupported legacy auth paths must not be allowed to widen public claims.

## Belief 3: Validation before refactor

The codebase should be stabilized through support evidence and regression protection before major structural rewrites.

## Belief 4: Small repo, high consequence

The repository is small, but it touches live Google user data. That demands stronger reliability discipline than the file count suggests.

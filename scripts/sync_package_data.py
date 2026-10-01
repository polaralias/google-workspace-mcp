"""Keep wheel assets identical to the root manifests and Health catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "google_workspace_mcp_data"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if packaged assets differ from root assets.")
    args = parser.parse_args()
    sources = sorted(ROOT.glob("tool_manifest_google*.json")) + [ROOT / "health_catalog.json"]
    if not all(path.exists() for path in sources):
        raise SystemExit("Root manifest or Health catalog is missing")
    stale = []
    for source in sources:
        target = TARGET / source.name
        if not target.exists() or target.read_bytes() != source.read_bytes():
            stale.append(source.name)
            if not args.check:
                target.write_bytes(source.read_bytes())
    if args.check and stale:
        raise SystemExit("Packaged data is stale: " + ", ".join(stale))
    print(f"Verified {len(sources)} packaged JSON assets" if args.check else f"Synced {len(sources)} packaged JSON assets")


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tool_support import render_tool_support_matrix


def main() -> None:
    output_path = REPO_ROOT / "docs" / "generated" / "tool-support-matrix.md"
    output_path.write_text(render_tool_support_matrix(), encoding="utf-8")


if __name__ == "__main__":
    main()

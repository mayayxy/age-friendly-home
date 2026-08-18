"""校验知识卡文件。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.store import reload_cards  # noqa: E402


def main() -> int:
    try:
        count = reload_cards()
    except Exception as exc:
        print(f"校验失败: {exc}")
        return 1
    print(f"校验通过，共 {count} 张知识卡")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

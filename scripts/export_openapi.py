"""Exporta o OpenAPI da API para docs/ e frontend/.

Uso (na raiz do monorepo):

    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
from pathlib import Path

from main import create_app

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ROOT / "docs" / "openapi.json",
    ROOT / "frontend" / "openapi.json",
)


def main() -> None:
    app = create_app(init_database=False, validate_config=False)
    payload = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    for path in TARGETS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

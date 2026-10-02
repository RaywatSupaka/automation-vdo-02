import json
from pathlib import Path

from smartflow.api import create_app
from smartflow.config import Settings

root = Path(__file__).resolve().parents[1]
app = create_app(Settings(root / "build" / "contract", "schema-generation-fixture-token", "test"))
target = root / "contracts" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
app.state.db.close()
print(target)

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    token: str
    mode: str = "dev"
    port: int = 8766

    @classmethod
    def from_env(cls):
        mode = os.getenv("SMARTFLOW_MODE", "dev")
        if mode not in {"dev", "prod", "test"}:
            raise ValueError("SMARTFLOW_MODE must be dev, prod or test")
        base = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "SmartFlowNext"
        default = base if mode == "prod" else Path.cwd() / ".smartflow"
        return cls(
            Path(os.getenv("SMARTFLOW_DATA_DIR", str(default))).resolve(),
            os.getenv("SMARTFLOW_API_TOKEN", ""),
            mode,
            int(os.getenv("SMARTFLOW_PORT", "8766")),
        )

    @property
    def db_path(self):
        return self.data_dir / "smartflow.db"

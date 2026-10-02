import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    token: str = field(repr=False)
    mode: str = "dev"
    port: int = 8766
    auth_mode: str = "local_session"
    session_role: str = "owner"
    diagnostics_token: str = field(default="", repr=False)

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
            os.getenv("SMARTFLOW_AUTH_MODE", "local_session"),
            os.getenv("SMARTFLOW_SESSION_ROLE", "owner"),
            os.getenv("SMARTFLOW_DIAGNOSTICS_TOKEN", ""),
        )

    @property
    def db_path(self):
        return self.data_dir / "smartflow.db"

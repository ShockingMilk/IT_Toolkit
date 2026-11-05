from pathlib import Path

from it_toolkit.utils.file_manager import read_json

class ConfigManager:
    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parents[3]
                / "config"
                / "toolkit.json"
            )

        self.config_path = config_path
        self.config = read_json(config_path)

    def get(
        self,
        key: str,
        default=None,
    ):
        value = self.config

        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            if part not in value:
                return default
            value = value[part]
        return value
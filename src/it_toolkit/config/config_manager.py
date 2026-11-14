import json

from importlib.resources import files
from pathlib import Path

class ConfigError(Exception):
    """Raised when toolkit configuration cannot be loaded."""

class ConfigManager:
    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parents[3]
                / "config"
                / "toolkit.json"
            )

        self.config_path = Path(config_path)

        if self.config_path.is_file():
            self.config = self._load_file(self.config_path)
        else:
            self.config = self._load_bundled_defaults()

        self._validate()

    @staticmethod
    def _load_file(path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise ConfigError(f"Unable to load configuration: {path}: {error}") from error

    @staticmethod
    def _load_bundled_defaults() -> dict:
        try:
            resource = files("it_toolkit.config").joinpath("default_toolkit.json")
            return json.loads(resource.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ModuleNotFoundError) as error:
            raise ConfigError(f"Unable to load bundled configuration: {error}") from error

    def _validate(self) -> None:
        if not isinstance(self.config, dict):
            raise ConfigError("The configuration root must be a JSON object.")

        required_sections = (
            "requirements",
            "reporting",
            "behavior",
        )

        for section in required_sections:
            if not isinstance(self.config.get(section), dict):
                raise ConfigError(f"Missing or invalid configuration section: {section}")

    def get(self, key: str,default=None):
        value = self.config

        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            if part not in value:
                return default
            value = value[part]
        return value
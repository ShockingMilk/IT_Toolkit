import json

from pathlib import Path

from it_toolkit.models.runtime_manifest import RuntimeManifest, RuntimeManifestError


class RuntimeRepositoryError(Exception):
    """Raised when a portable runtime repository cannot be read."""


class RuntimeCatalogManager:
    MANIFEST_FILENAME = "manifest.json"

    def __init__(self, repository_path: Path):
        self.repository_path = Path(repository_path).resolve()
        self.manifest_path = self.repository_path / self.MANIFEST_FILENAME

    def load_manifest(self) -> RuntimeManifest:
        if not self.repository_path.is_dir():
            raise RuntimeRepositoryError(f"Runtime repository directory does not exist: {self.repository_path}")

        if not self.manifest_path.is_file():
            raise RuntimeRepositoryError(f"Runtime manifest not found: {self.manifest_path}")

        try:
            with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
                data = json.load(manifest_file)

            return RuntimeManifest.from_dict(data)

        except (
            OSError,
            json.JSONDecodeError,
            RuntimeManifestError,
        ) as error:
            raise RuntimeRepositoryError(f"Unable to load runtime manifest: {error}") from error

    def list_runtimes(self):
        """Return all runtime entries in the local manifest."""
        return self.load_manifest().runtimes

    def get_runtime(
        self,
        runtime_id: str,
        version: str,
    ):
        """Return one exact runtime/version entry."""
        manifest = self.load_manifest()

        for entry in manifest.runtimes:
            if entry.runtime_id == runtime_id and entry.version == version:
                return entry

        raise RuntimeRepositoryError(f"Runtime not found: {runtime_id} {version}")

    def resolve_archive_path(self, entry) -> Path:
        """Resolve an archive path and prevent repository escape."""
        candidate = (self.repository_path / Path(entry.archive)).resolve()

        try:
            candidate.relative_to(self.repository_path)
        except ValueError as error:
            raise RuntimeRepositoryError(f"Runtime archive escapes repository: {entry.archive}") from error

        return candidate

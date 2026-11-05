import json

from pathlib import Path


def ensure_directory(path: Path) -> Path:

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


def read_json(path: Path) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def write_json(
    path: Path,
    data: dict,
) -> None:

    ensure_directory(path.parent)

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
        )

    temporary_path.replace(path)
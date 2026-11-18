import hashlib
from pathlib import Path


def calculate_sha256(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """Calculate the SHA-256 checksum of a file."""

    path = Path(path)

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)

    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> bool:
    """Compare a file's SHA-256 checksum with an expected value."""

    if not isinstance(expected, str):
        raise TypeError("Expected checksum must be a string.")

    return calculate_sha256(path).lower() == expected.lower()
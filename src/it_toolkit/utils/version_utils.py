import re


def parse_version(version: str) -> tuple[int, ...]:
    """
    Convert a version string into a comparable tuple.

    Examples:
        5.1       -> (5, 1)
        7.4.2     -> (7, 4, 2)
        v7.6.0    -> (7, 6, 0)
    """

    if not version:
        return ()

    matches = re.findall(r"\d+", version)

    return tuple(int(value) for value in matches)


def version_at_least(
    current: str,
    minimum: str,
) -> bool:
    """
    Determine whether current meets the minimum version.
    """

    current_parts = parse_version(current)
    minimum_parts = parse_version(minimum)

    if not current_parts or not minimum_parts:
        return False

    length = max(
        len(current_parts),
        len(minimum_parts),
    )

    current_parts += (0,) * (length - len(current_parts))
    minimum_parts += (0,) * (length - len(minimum_parts))

    return current_parts >= minimum_parts
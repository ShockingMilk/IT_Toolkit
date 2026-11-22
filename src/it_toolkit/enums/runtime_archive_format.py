from enum import Enum


class RuntimeArchiveFormat(str, Enum):
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_XZ = "tar.xz"
    TAR_BZ2 = "tar.bz2"
import platform
import sys

from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.detectors.base_detector import BaseDetector
from it_toolkit.models.python_info import PythonInfo
from it_toolkit.utils.version_utils import version_at_least

class PythonDetector(BaseDetector):
    def __init__(self, config: ConfigManager):
        self.config = config

    def detect(self) -> PythonInfo:
        version = platform.python_version()
        minimum = self.config.get(
            "requirements.python.minimum_version",
            "3.10",
        )

        return PythonInfo(
            installed=True,
            version=version,
            executable=sys.executable,
            implementation=platform.python_implementation(),
            meets_requirement=version_at_least(
                version,
                minimum,
            ),
        )
from pathlib import Path

from it_toolkit.models.system_profile import SystemProfile
from it_toolkit.utils.file_manager import write_json

class ReportManager:
    def __init__(self, report_directory: Path):
        self.report_directory = report_directory

    def save_system_profile(
        self,
        profile: SystemProfile,
        filename: str = "system_profile.json",
    ) -> Path:
        report_path = (
            self.report_directory / filename
        )

        write_json(
            report_path,
            profile.to_dict(),
        )
        return report_path
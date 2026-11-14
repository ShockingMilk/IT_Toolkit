from pathlib import Path

from it_toolkit.models.system_profile import SystemProfile
from it_toolkit.utils.file_manager import write_json

class ReportManager:
    def __init__(self, report_directory: Path):
        self.report_directory = Path(report_directory)

    def save_system_profile(
        self,
        profile: SystemProfile,
        filename: str = "system_profile.json",
    ) -> Path:
        report_name = Path(filename)

        if report_name.is_absolute() or len(report_name.parts) != 1 or report_name.name in ("", ".", ".."):
            raise ValueError("Report filename must be a simple filename inside the reports directory.")

        report_path = self.report_directory / report_name
        
        write_json(
            report_path,
            profile.to_dict(),
        )
        return report_path
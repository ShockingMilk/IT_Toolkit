from datetime import datetime
from pathlib import Path

from it_toolkit.models.system_profile import SystemProfile
from it_toolkit.modules.results import DiagnosticResult
from it_toolkit.utils.file_manager import write_json


class ReportManager:

    def __init__(self, report_directory: Path):
        self.report_directory = Path(report_directory)

    @staticmethod
    def _validate_filename(filename: str) -> Path:
        report_name = Path(filename)

        if (
            report_name.is_absolute()
            or len(report_name.parts) != 1
            or report_name.name in ("", ".", "..")
        ):
            raise ValueError(
                "Report filename must be a simple filename."
            )

        return report_name

    def save_system_profile(
        self,
        profile: SystemProfile,
        filename: str = "system_profile.json",
    ) -> Path:

        report_name = self._validate_filename(filename)

        report_path = self.report_directory / report_name

        write_json(
            report_path,
            profile.to_dict(),
        )

        return report_path

    def save_diagnostic_result(
        self,
        result: DiagnosticResult,
    ) -> Path:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        safe_module_id = "".join(
            character if character.isalnum() or character in "-_"
            else "_"
            for character in result.module_id
        )

        filename = (
            f"{safe_module_id}_{timestamp}.json"
        )

        diagnostic_directory = (
            self.report_directory / "diagnostics"
        )

        report_path = diagnostic_directory / filename

        write_json(
            report_path,
            result.to_dict(),
        )

        return report_path
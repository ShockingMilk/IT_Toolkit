from pathlib import Path

from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.managers.detection_manager import DetectionManager
from it_toolkit.managers.capability_manager import CapabilityManager
from it_toolkit.managers.report_manager import ReportManager

class Application:
    def __init__(self):
        self.root = Path(__file__).resolve().parents[3]
        self.config = ConfigManager(
            self.root / "config" / "toolkit.json"
        )
        self.detection_manager = DetectionManager(
            self.config
        )
        self.capability_manager = CapabilityManager()
        self.report_manager = ReportManager(
            self.root / "reports"
        )

    def run(self):
        print("\nInitializing IT Toolkit...\n")

        # Step 1: Detect system
        profile = self.detection_manager.detect()

        # Step 2: Evaluate capabilities
        profile.capabilities = (
            self.capability_manager.evaluate(profile)
        )

        # Step 3: Save system report
        report_path = None

        if self.config.get("reporting.enabled", True):
            filename = self.config.get(
                "reporting.filename",
                "system_profile.json",
            )
            report_path = (
                self.report_manager.save_system_profile(
                    profile,
                    filename,
                )
            )

        # Step 4: Display results
        self.display_profile(profile)
        if report_path:
            print(f"\nSystem profile saved: {report_path}")

        return profile

    @staticmethod
    def display_profile(profile):
        print("=" * 55)
        print("                   IT TOOLKIT")
        print("=" * 55)
        print("\nSYSTEM")
        print(f"  Hostname     : {profile.hostname}")
        print(f"  Username     : {profile.username}")
        print("\nOPERATING SYSTEM")
        print(f"  OS           : {profile.operating_system.name}")
        print(f"  Distribution : {profile.operating_system.distribution}")
        print(f"  Version      : {profile.operating_system.version}")
        print(f"  Architecture : {profile.operating_system.architecture.value}")
        print(f"  Kernel       : {profile.operating_system.kernel}")
        print("\nRUNTIME")
        print(f"  Shell        : {profile.shell.value}")
        print(f"  Python       : {profile.python.version}")
        print(f"  Python Path  : {profile.python.executable}")
        print("\nPOWERSHELL")

        if not profile.powershell:
            print("  No PowerShell installations detected.")

        for installation in profile.powershell:
            print(
                f"  Version      : {installation.version}"
            )
            print(
                f"  Edition      : {installation.edition.value}"
            )
            print(
                f"  Status       : {installation.status.value}"
            )
            print(
                f"  Meets Minimum: {installation.meets_requirement}"
            )
            print(
                f"  Executable   : {installation.executable}"
            )
            print()

        print("\nTOOLKIT MODE")
        print(f"  {profile.toolkit_mode.value}")
        print("\nCAPABILITIES")

        for capability in profile.capabilities:
            status = (
                "AVAILABLE"
                if capability.available
                else "UNAVAILABLE"
            )
            print(
                f"  [{status}] {capability.name.value}"
            )
        print("\n" + "=" * 55)
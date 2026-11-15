from pathlib import Path

from it_toolkit.config.config_manager import ConfigManager
from it_toolkit.managers.detection_manager import DetectionManager
from it_toolkit.managers.capability_manager import CapabilityManager
from it_toolkit.managers.report_manager import ReportManager
from it_toolkit.menus.menu_manager import MenuManager

class Application:
    def __init__(self):
        self.root = Path(__file__).resolve().parents[3]
        self.config = ConfigManager(self.root / "config/toolkit.json")
        self.detection_manager = DetectionManager(self.config)
        self.capability_manager = CapabilityManager()
        self.report_manager = ReportManager(self.root / "reports")
        self.menu_manager = MenuManager()

    def run(self):
        print("\nInitializing IT Toolkit...\n")

        # Step 1: Detect system
        profile = self.detection_manager.detect()

        # Step 2: Evaluate capabilities
        profile.capabilities = self.capability_manager.evaluate(profile)

        # Step 3: Generate system report
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

        # Step 4: Display startup summary
        self.display_startup_summary(profile)

        # Step 5: Launch interactive menu
        handlers = {
            "system_profile": lambda: self.display_profile(profile=profile),
            "capability_status": lambda: self.display_capabilities(profile),
            "report_information": lambda: self.display_report(report_path)
        }

        self.menu_manager.run(profile=profile, handlers=handlers)

        return profile

    @staticmethod
    def display_startup_summary(profile):
        print("=" * 55)
        print("                   IT TOOLKIT")
        print("=" * 55)

        print(f"\nOperating System : {profile.operating_system.name}")
        print(f"Architecture     : {profile.operating_system.architecture.value}")
        print(f"Toolkit Mode     : {profile.toolkit_mode.value}")

        print("\nInitialization complete.")

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
        
        print("\nPython")
        print(f"  Version      : {profile.python.version}")
        print(f"  Executable   : {profile.python.executable}")
        
        print("\nPOWERSHELL")

        if not profile.powershell:
            print("  No PowerShell installations detected.")

        for installation in profile.powershell:
            print(f"\n  Version      : {installation.version}")
            print(f"  Edition      : {installation.edition.value}")
            print(f"  Status       : {installation.status.value}")
            print(f"  Meets Minimum: {installation.meets_requirement}")
            print(f"  Executable   : {installation.executable}")

        print("\nTOOLKIT MODE")
        print(f"  {profile.toolkit_mode.value}")

        print("\n" + "=" * 55)

    @staticmethod
    def display_capabilities(profile):
        print("\n" + "=" * 55)
        print("CAPABILITIES STATUS")
        print("=" * 55)

        for capability in profile.capabilities:
            status = "AVAILABLE" if capability.available else "UNAVAILABLE"
            print(f"\n[{status}] {capability.name.value}")

            if capability.reason:
                print(f"   {capability.reason}")

        print("\n" + "=" * 55)

    @staticmethod
    def display_report(report_path):
        print("\n" + "=" * 55)
        print("REPORT INFORMATION")
        print("=" * 55)

        if report_path:
            print("\nSystem report generated:")
            print(f"   {report_path}")
        else:
            print("\nReport generation is disabled.")

        print("\n" + "=" * 55)
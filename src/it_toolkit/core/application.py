from pathlib import Path

from it_toolkit.config.config_manager import ConfigManager

from it_toolkit.managers.detection_manager import DetectionManager
from it_toolkit.managers.capability_manager import CapabilityManager
from it_toolkit.managers.report_manager import ReportManager

from it_toolkit.menus.menu_manager import MenuManager

from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.registry import ModuleRegistry
from it_toolkit.modules.runner import ModuleRunner

from it_toolkit.modules.builtin import register_builtin_modules


class Application:

    def __init__(self):

        self.root = Path(__file__).resolve().parents[3]

        self.config = ConfigManager(
            self.root / "config/toolkit.json"
        )

        self.detection_manager = DetectionManager(
            self.config
        )

        self.capability_manager = CapabilityManager()

        self.report_manager = ReportManager(
            self.root / "reports"
        )

        self.menu_manager = MenuManager()

        # Diagnostic framework
        self.module_registry = ModuleRegistry()

        register_builtin_modules(
            self.module_registry
        )

        self.module_runner = ModuleRunner(
            registry=self.module_registry,
            allow_system_changes=False,
        )

    def run(self):

        print("\nInitializing IT Toolkit...\n")

        # Step 1: Detect system
        profile = self.detection_manager.detect()

        # Step 2: Evaluate capabilities
        profile.capabilities = (
            self.capability_manager.evaluate(profile)
        )

        # Step 3: Generate system report
        reporting_enabled = self.config.get(
            "reporting.enabled",
            True,
        )

        report_path = None

        if reporting_enabled:

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

        # Step 4: Create module context
        module_context = ModuleContext(
            profile=profile,
            toolkit_root=self.root,
            config=self.config.config,
        )

        # Step 5: Display startup summary
        self.display_startup_summary(profile)

        # Step 6: Launch interactive menu
        handlers = {
            "system_profile": lambda: self.display_profile(
                profile
            ),

            "capability_status": lambda: self.display_capabilities(
                profile
            ),

            "report_information": lambda: self.display_report(
                report_path
            ),
        }

        self.menu_manager.run(
            profile=profile,
            handlers=handlers,
            module_registry=self.module_registry,
            module_runner=self.module_runner,
            module_context=module_context,
            on_diagnostic_result=(
                self._save_diagnostic_result
                if reporting_enabled
                else None
            ),
            reporting_enabled=reporting_enabled,
        )

        return profile

    def _save_diagnostic_result(self, result):

        return self.report_manager.save_diagnostic_result(
            result
        )

    @staticmethod
    def display_startup_summary(profile):

        print("=" * 55)
        print("                   IT TOOLKIT")
        print("=" * 55)

        print(
            f"\nOperating System : {profile.operating_system.name}"
        )

        print(
            f"Architecture     : {profile.operating_system.architecture.value}"
        )

        print(
            f"Toolkit Mode     : {profile.toolkit_mode.value}"
        )

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

        print("\nSHELL")
        print(f"  {profile.shell.value}")

        print("\nPYTHON")
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

            status = (
                "AVAILABLE"
                if capability.available
                else "UNAVAILABLE"
            )

            print(
                f"\n[{status}] {capability.name.value}"
            )

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

            print("\nDiagnostic reports are saved under:")
            print("   reports/diagnostics/")

        else:
            print("\nReport generation is disabled.")

        print("\n" + "=" * 55)
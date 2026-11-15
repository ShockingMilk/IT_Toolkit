from collections.abc import Callable
from pathlib import Path

from it_toolkit.menus.main_menu import MainMenu
from it_toolkit.menus.menu_view import MenuView
from it_toolkit.menus.menu_item import MenuItem
from it_toolkit.models.system_profile import SystemProfile

from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.registry import ModuleRegistry
from it_toolkit.modules.runner import ModuleRunner
from it_toolkit.modules.results import DiagnosticResult


class MenuManager:

    def __init__(
        self,
        view: MenuView | None = None,
        main_menu: MainMenu | None = None,
    ):
        self.view = view or MenuView()
        self.main_menu = main_menu or MainMenu()

    def run(
        self,
        profile: SystemProfile,
        handlers: dict[str, Callable[[], None]],
        module_registry: ModuleRegistry | None = None,
        module_runner: ModuleRunner | None = None,
        module_context: ModuleContext | None = None,
        on_diagnostic_result: Callable[
            [DiagnosticResult], Path | None
        ] | None = None,
        reporting_enabled: bool = True,
    ) -> None:

        diagnostics_enabled = all(
            item is not None
            for item in (
                module_registry,
                module_runner,
                module_context,
            )
        )

        items = self.main_menu.build(
            profile=profile,
            reporting_enabled=reporting_enabled,
            include_diagnostics=diagnostics_enabled,
        )

        while True:

            choice = self.view.display(
                title="IT TOOLKIT - MAIN MENU",
                items=items,
            )

            if choice == "0":
                self.view.output("\nExiting IT Toolkit.")
                return

            if choice == "diagnostics":
                self._run_diagnostics(
                    registry=module_registry,
                    runner=module_runner,
                    context=module_context,
                    result_handler=on_diagnostic_result,
                )
                continue

            handler = handlers.get(choice)

            if handler is None:
                self.view.output(
                    "\nThis menu action is not implemented."
                )
            else:
                handler()

            self._pause()

    def _run_diagnostics(
        self,
        registry: ModuleRegistry,
        runner: ModuleRunner,
        context: ModuleContext,
        result_handler: Callable[
            [DiagnosticResult], Path | None
        ] | None = None,
    ) -> None:

        while True:

            compatible_modules = runner.list_compatible(context)

            items = [
                MenuItem(
                    key=module.definition.module_id,
                    label=module.definition.name,
                    action=module.definition.module_id,
                    description=module.definition.description,
                )
                for module in compatible_modules
            ]

            if not items:
                self.view.output(
                    "\nNo compatible diagnostic modules are currently available."
                )
                self._pause()
                return

            choice = self.view.display(
                title="IT TOOLKIT - DIAGNOSTICS",
                items=items,
                allow_back=True,
            )

            if choice == "0":
                return

            try:
                result = runner.run(
                    module_id=choice,
                    context=context,
                )

                self._display_result(result)

                if result_handler is not None:
                    report_path = result_handler(result)

                    if report_path:
                        self.view.output(
                            f"\nDiagnostic report saved: {report_path}"
                        )

            except Exception as error:
                self.view.output(
                    f"\nUnable to complete diagnostic: {error}"
                )

            self._pause()

    def _display_result(
        self,
        result: DiagnosticResult,
    ) -> None:

        self.view.output("\n" + "=" * 55)
        self.view.output(result.module_name.upper())
        self.view.output("=" * 55)

        self.view.output(
            f"\nStatus: {result.status.value.upper()}"
        )

        self.view.output(f"\n{result.summary}")

        if result.data:
            self.view.output("\nRESULT DATA")

            for key, value in result.data.items():
                self.view.output(f"\n{key}: {value}")

        if result.warnings:
            self.view.output("\nWARNINGS")

            for warning in result.warnings:
                self.view.output(f"  - {warning}")

        if result.errors:
            self.view.output("\nERRORS")

            for error in result.errors:
                self.view.output(f"  - {error}")

        if result.duration_seconds is not None:
            self.view.output(
                f"\nExecution time: {result.duration_seconds:.4f} seconds"
            )

        self.view.output("\n" + "=" * 55)

    def _pause(self) -> None:
        try:
            self.view.input(
                "\nPress Enter to return to the menu..."
            )
        except EOFError:
            return
        except KeyboardInterrupt:
            raise
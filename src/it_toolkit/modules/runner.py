from datetime import datetime, timezone
from time import perf_counter

from it_toolkit.enums import (
    DiagnosticStatus,
    ModuleSafety,
)

from it_toolkit.modules.compatibility import CompatibilityChecker
from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.registry import ModuleRegistry
from it_toolkit.modules.results import DiagnosticResult


class ModuleRunner:

    def __init__(
        self,
        registry: ModuleRegistry,
        compatibility_checker: CompatibilityChecker | None = None,
        allow_system_changes: bool = False,
    ):
        self.registry = registry

        self.compatibility_checker = (
            compatibility_checker or CompatibilityChecker()
        )

        self.allow_system_changes = allow_system_changes

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_compatible(
        self,
        context: ModuleContext,
    ):
        compatible = []

        for module in self.registry.list_all():
            definition = module.definition

            if (
                definition.safety == ModuleSafety.SYSTEM_CHANGE
                and not self.allow_system_changes
            ):
                continue

            if not self.compatibility_checker.check(
                definition,
                context,
            ):
                compatible.append(module)

        return compatible

    def run(
        self,
        module_id: str,
        context: ModuleContext,
    ) -> DiagnosticResult:

        try:
            module = self.registry.get(module_id)
        except KeyError as error:
            return DiagnosticResult(
                module_id=module_id,
                module_name=module_id,
                status=DiagnosticStatus.FAILED,
                summary="The requested module is not registered.",
                errors=[str(error)],
            )

        definition = module.definition

        started_at = self._timestamp()
        timer_start = perf_counter()

        def finalize(result: DiagnosticResult) -> DiagnosticResult:
            result.module_id = definition.module_id
            result.module_name = definition.name
            result.started_at = started_at
            result.completed_at = self._timestamp()
            result.duration_seconds = round(
                perf_counter() - timer_start,
                6,
            )
            return result

        if (
            definition.safety == ModuleSafety.SYSTEM_CHANGE
            and not self.allow_system_changes
        ):
            return finalize(
                DiagnosticResult(
                    module_id=definition.module_id,
                    module_name=definition.name,
                    status=DiagnosticStatus.SKIPPED,
                    summary="Execution blocked by the read-only safety policy.",
                    warnings=[
                        "This module is classified as system-changing."
                    ],
                )
            )

        compatibility_issues = self.compatibility_checker.check(
            definition,
            context,
        )

        if compatibility_issues:
            return finalize(
                DiagnosticResult(
                    module_id=definition.module_id,
                    module_name=definition.name,
                    status=DiagnosticStatus.SKIPPED,
                    summary="Module is not compatible with this system.",
                    warnings=compatibility_issues,
                )
            )

        try:
            result = module.run(context)

            if not isinstance(result, DiagnosticResult):
                raise TypeError(
                    "Module must return a DiagnosticResult."
                )

            return finalize(result)

        except Exception as error:
            return finalize(
                DiagnosticResult(
                    module_id=definition.module_id,
                    module_name=definition.name,
                    status=DiagnosticStatus.FAILED,
                    summary="The diagnostic module encountered an error.",
                    errors=[
                        f"{type(error).__name__}: {error}"
                    ],
                )
            )
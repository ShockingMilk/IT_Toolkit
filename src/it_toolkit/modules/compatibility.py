import importlib.util
import shutil

from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.definition import ModuleDefinition
from it_toolkit.enums import DependencyType


class CompatibilityChecker:

    def check(
        self,
        definition: ModuleDefinition,
        context: ModuleContext,
    ) -> list[str]:

        reasons = []

        operating_system = context.profile.operating_system.family

        if operating_system not in definition.supported_operating_systems:
            reasons.append(
                f"Unsupported operating system: {operating_system.value}"
            )

        available_capabilities = {
            capability.name
            for capability in context.profile.capabilities
            if capability.available
        }

        for capability in definition.required_capabilities:
            if capability not in available_capabilities:
                reasons.append(
                    f"Required capability unavailable: {capability.value}"
                )

        for dependency in definition.dependencies:

            if dependency.dependency_type == DependencyType.EXECUTABLE:
                if shutil.which(dependency.name) is None:
                    reasons.append(
                        f"Required executable not found: {dependency.name}"
                    )

            elif dependency.dependency_type == DependencyType.PYTHON_MODULE:
                try:
                    available = (
                        importlib.util.find_spec(dependency.name)
                        is not None
                    )
                except (ImportError, ValueError, AttributeError):
                    available = False

                if not available:
                    reasons.append(
                        f"Required Python module not found: {dependency.name}"
                    )

        return reasons
import json
import unittest

from types import SimpleNamespace

from it_toolkit.enums import (
    CapabilityType,
    DiagnosticStatus,
    ModuleSafety,
    OperatingSystem,
)

from it_toolkit.modules.base import DiagnosticModule
from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.definition import ModuleDefinition
from it_toolkit.enums import DependencyType
from it_toolkit.modules.dependency import ModuleDependency
from it_toolkit.modules.registry import ModuleRegistry
from it_toolkit.modules.runner import ModuleRunner
from it_toolkit.modules.results import DiagnosticResult


def create_context(
    operating_system=OperatingSystem.LINUX,
    capabilities=None,
):

    if capabilities is None:
        capabilities = [
            SimpleNamespace(
                name=CapabilityType.SYSTEM_INFORMATION,
                available=True,
            )
        ]

    profile = SimpleNamespace(
        operating_system=SimpleNamespace(
            family=operating_system,
        ),
        capabilities=capabilities,
    )

    return ModuleContext(
        profile=profile,
        toolkit_root=".",
        config={},
    )


class SuccessfulModule(DiagnosticModule):

    _definition = ModuleDefinition(
        module_id="test.success",
        name="Successful Test",
        category="Testing",
        description="Test module.",
        supported_operating_systems=(
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
            OperatingSystem.MACOS,
        ),
        required_capabilities=(
            CapabilityType.SYSTEM_INFORMATION,
        ),
    )

    @property
    def definition(self):
        return self._definition

    def run(self, context):

        return DiagnosticResult(
            module_id=self.definition.module_id,
            module_name=self.definition.name,
            status=DiagnosticStatus.SUCCESS,
            summary="Test completed.",
            data={"result": "passed"},
        )


class FailingModule(SuccessfulModule):

    _definition = ModuleDefinition(
        module_id="test.failure",
        name="Failing Test",
        category="Testing",
        description="Test module that raises an exception.",
        supported_operating_systems=(
            OperatingSystem.WINDOWS,
            OperatingSystem.LINUX,
            OperatingSystem.MACOS,
        ),
    )

    def run(self, context):
        raise RuntimeError("Intentional test failure.")


class WindowsOnlyModule(SuccessfulModule):

    _definition = ModuleDefinition(
        module_id="test.windows",
        name="Windows Only Test",
        category="Testing",
        description="Windows-only module.",
        supported_operating_systems=(
            OperatingSystem.WINDOWS,
        ),
    )


class MissingDependencyModule(SuccessfulModule):

    _definition = ModuleDefinition(
        module_id="test.dependency",
        name="Missing Dependency Test",
        category="Testing",
        description="Test module with a missing executable.",
        supported_operating_systems=(
            OperatingSystem.LINUX,
            OperatingSystem.WINDOWS,
            OperatingSystem.MACOS,
        ),
        dependencies=(
            ModuleDependency(
                name="it-toolkit-nonexistent-test-command",
                dependency_type=DependencyType.EXECUTABLE,
            ),
        ),
    )


class SystemChangeModule(SuccessfulModule):

    _definition = ModuleDefinition(
        module_id="test.system_change",
        name="System Change Test",
        category="Testing",
        description="Test module that requires system changes.",
        supported_operating_systems=(
            OperatingSystem.LINUX,
            OperatingSystem.WINDOWS,
            OperatingSystem.MACOS,
        ),
        safety=ModuleSafety.SYSTEM_CHANGE,
    )


class ModuleRegistryTests(unittest.TestCase):

    def setUp(self):
        self.registry = ModuleRegistry()

    def test_register_module(self):

        self.registry.register(SuccessfulModule())

        self.assertEqual(
            len(self.registry),
            1,
        )

    def test_duplicate_registration_rejected(self):

        self.registry.register(SuccessfulModule())

        with self.assertRaises(ValueError):
            self.registry.register(SuccessfulModule())

    def test_retrieve_module(self):

        module = SuccessfulModule()

        self.registry.register(module)

        retrieved = self.registry.get(
            "test.success"
        )

        self.assertIs(
            retrieved,
            module,
        )

    def test_unknown_module_raises_key_error(self):

        with self.assertRaises(KeyError):
            self.registry.get("missing.module")


class ModuleRunnerTests(unittest.TestCase):

    def setUp(self):

        self.registry = ModuleRegistry()

        self.registry.register(
            SuccessfulModule()
        )

        self.registry.register(
            FailingModule()
        )

        self.runner = ModuleRunner(
            registry=self.registry
        )

        self.context = create_context()

    def test_successful_execution(self):

        result = self.runner.run(
            "test.success",
            self.context,
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SUCCESS,
        )

        self.assertEqual(
            result.data["result"],
            "passed",
        )

    def test_module_failure_is_isolated(self):

        result = self.runner.run(
            "test.failure",
            self.context,
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.FAILED,
        )

        self.assertTrue(result.errors)

        # A separate module can still execute.
        successful_result = self.runner.run(
            "test.success",
            self.context,
        )

        self.assertEqual(
            successful_result.status,
            DiagnosticStatus.SUCCESS,
        )

    def test_unknown_module_returns_failed_result(self):

        result = self.runner.run(
            "missing.module",
            self.context,
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.FAILED,
        )

    def test_result_is_json_serializable(self):

        result = self.runner.run(
            "test.success",
            self.context,
        )

        serialized = json.dumps(
            result.to_dict()
        )

        self.assertIsInstance(
            serialized,
            str,
        )

    def test_execution_timing_is_recorded(self):

        result = self.runner.run(
            "test.success",
            self.context,
        )

        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)
        self.assertIsNotNone(result.duration_seconds)


class ModuleCompatibilityTests(unittest.TestCase):

    def setUp(self):

        self.registry = ModuleRegistry()

        self.registry.register(
            WindowsOnlyModule()
        )

        self.registry.register(
            MissingDependencyModule()
        )

        self.runner = ModuleRunner(
            registry=self.registry
        )

    def test_unsupported_os_is_skipped(self):

        context = create_context(
            operating_system=OperatingSystem.LINUX
        )

        result = self.runner.run(
            "test.windows",
            context,
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SKIPPED,
        )

    def test_missing_dependency_is_skipped(self):

        context = create_context()

        result = self.runner.run(
            "test.dependency",
            context,
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SKIPPED,
        )

        self.assertTrue(result.warnings)


class ModuleSafetyTests(unittest.TestCase):

    def setUp(self):

        self.registry = ModuleRegistry()

        self.registry.register(
            SystemChangeModule()
        )

        self.context = create_context()

    def test_system_change_module_blocked_by_default(self):

        runner = ModuleRunner(
            registry=self.registry
        )

        result = runner.run(
            "test.system_change",
            self.context,
        )

        self.assertEqual(
            result.status,
            DiagnosticStatus.SKIPPED,
        )

    def test_system_change_module_not_listed_by_default(self):

        runner = ModuleRunner(
            registry=self.registry
        )

        compatible = runner.list_compatible(
            self.context
        )

        self.assertEqual(
            compatible,
            [],
        )


if __name__ == "__main__":
    unittest.main()
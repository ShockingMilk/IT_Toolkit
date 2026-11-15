from abc import ABC, abstractmethod

from it_toolkit.modules.context import ModuleContext
from it_toolkit.modules.definition import ModuleDefinition
from it_toolkit.modules.results import DiagnosticResult


class DiagnosticModule(ABC):

    @property
    @abstractmethod
    def definition(self) -> ModuleDefinition:
        """
        Return the module's metadata.
        """

    @abstractmethod
    def run(self, context: ModuleContext) -> DiagnosticResult:
        """
        Execute the diagnostic and return a standardized result.

        Implementations should be read-only unless explicitly
        designed and authorized for a future system-changing workflow.
        """
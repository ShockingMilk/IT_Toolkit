from it_toolkit.modules.base import DiagnosticModule


class ModuleRegistry:

    def __init__(self):
        self._modules: dict[str, DiagnosticModule] = {}

    def register(self, module: DiagnosticModule) -> None:
        module_id = module.definition.module_id

        if module_id in self._modules:
            raise ValueError(
                f"Module already registered: {module_id}"
            )

        self._modules[module_id] = module

    def unregister(self, module_id: str) -> None:
        if module_id not in self._modules:
            raise KeyError(
                f"Unknown module: {module_id}"
            )

        del self._modules[module_id]

    def get(self, module_id: str) -> DiagnosticModule:
        try:
            return self._modules[module_id]
        except KeyError as error:
            raise KeyError(
                f"Unknown module: {module_id}"
            ) from error

    def list_all(self) -> list[DiagnosticModule]:
        return sorted(
            self._modules.values(),
            key=lambda module: (
                module.definition.category,
                module.definition.name,
            ),
        )

    def list_by_category(
        self,
        category: str,
    ) -> list[DiagnosticModule]:

        return [
            module
            for module in self.list_all()
            if module.definition.category == category
        ]

    def __len__(self) -> int:
        return len(self._modules)
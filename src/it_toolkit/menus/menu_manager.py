from collections.abc import Callable

from it_toolkit.menus.main_menu import MainMenu
from it_toolkit.menus.menu_view import MenuView
from it_toolkit.models.system_profile import SystemProfile

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
    ) -> None:
        items = self.main_menu.build(profile=profile)

        while True:
            choice = self.view.display(
                title="IT TOOLKIT - MAIN MENU",
                items=items
            )

            if choice == "0":
                self.view.output("\nExiting IT Toolkit.")
                return

            handler = handlers.get(choice)

            if handler is None:
                self.view.output("\nThis menu action is not implemented.")
            else:
                handler()

            self._pause()

    def _pause(self) -> None:
        try:
            self.view.input("\nPress Enter to return to the menu...")
        except (EOFError, KeyboardInterrupt):
            return
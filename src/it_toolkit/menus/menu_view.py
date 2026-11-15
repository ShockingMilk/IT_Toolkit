from collections.abc import Callable, Sequence

from it_toolkit.menus.menu_item import MenuItem

class MenuView:
    def __init__(
        self,
        input_function: Callable[[str], str] = input,
        output_function: Callable[[str], None] = print,
    ):
        self.input = input_function
        self.output = output_function

    def display(
        self, 
        title: str,
        items: Sequence[MenuItem],
        allow_back: bool = False,
    ) -> str:
        self.output("\n" + "=" * 55)
        self.output(title.center(55))
        self.output("=" * 55)

        for index, item in enumerate(items, start=1):
            self.output(f"   {index}. {item.label}")

            if item.description:
                self.output(f"       {item.description}")

        self.output("")

        if allow_back:
            self.output("   0. Back")
        else:
            self.output("   0. Exit")

        self.output("-" * 55)

        valid_choices = {
            str(index)
            for index in range(1, len(items) + 1)
        }
        valid_choices.add("0")

        while True:
            try:
                choice = self.input("Select an option: ").strip()
            except (EOFError, KeyboardInterrupt):
                return "0"

            if choice in valid_choices:
                if choice == "0":
                    return "0"

                return items[int(choice) - 1].key

            self.output("Invalid selection. Please try again.")
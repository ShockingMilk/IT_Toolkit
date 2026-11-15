import unittest

from it_toolkit.menus.menu_item import MenuItem
from it_toolkit.menus.menu_view import MenuView

class TestMenuView(unittest.TestCase):
    def test_valid_selection(self):
        responses = iter(["2"])
        output = []

        view = MenuView(
            input_function=lambda _: next(responses),
            output_function=output.append,
        )

        items = [
            MenuItem("one", "First", "first"),
            MenuItem("two", "Second", "second"),
        ]

        result = view.display("TEST MENU", items)

        self.assertEqual(result, "two")

    def test_zero_selection(self):
        view = MenuView(
            input_function=lambda _: "0",
            output_function=lambda _: None,
        )

        result = view.display("TEST MENU", [])

        self.assertEqual(result, "0")

    def test_invalid_selection_retries(self):
        responses = iter(["invalid", "9", "1"])

        view = MenuView(
            input_function=lambda _: next(responses),
            output_function=lambda _: None,
        )

        items = [
            MenuItem("one", "First", "first"),
        ]

        result = view.display("TEST MENU", items)

        self.assertEqual(result, "one")

    def test_eof_returns_exit(self):
        def raise_eof(_):
            raise EOFError

        view = MenuView(
            input_function=raise_eof,
            output_function=lambda _: None,
        )

        result = view.display("TEST MENU", [])

        self.assertEqual(result, "0")

if __name__ == "__main__":
    unittest.main()
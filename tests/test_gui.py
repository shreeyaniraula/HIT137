import unittest
from types import SimpleNamespace

from src.gui import PuzzleGUI


class DummyCanvas:
    def __init__(self, width=300, height=300):
        self._width = width
        self._height = height

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height


class TestGUI(unittest.TestCase):
    def test_gui_initialises_with_default_grid_and_model_binding(self):
        gui = PuzzleGUI(root=None)

        self.assertEqual(gui.get_grid_size(), 3)
        self.assertIsNotNone(gui.get_puzzle())
        self.assertEqual(gui.get_moves(), 0)
        self.assertEqual(gui.get_incorrect_count(), 0)

    def test_grid_size_update_and_model_reset(self):
        gui = PuzzleGUI(root=None)
        gui.set_grid_size(4)

        self.assertEqual(gui.get_grid_size(), 4)
        self.assertEqual(gui.get_puzzle().get_grid_size(), 4)

        gui.reset_puzzle()
        self.assertEqual(gui.get_moves(), 0)
        self.assertEqual(gui.get_incorrect_count(), 0)

    def test_click_to_index_stays_in_bounds_for_each_cell(self):
        gui = PuzzleGUI(root=None)
        gui._grid_size = 3
        gui._playable_canvas = DummyCanvas(300, 300)

        checks = {
            (10, 10): 0,
            (110, 10): 1,
            (210, 10): 2,
            (10, 110): 3,
            (110, 110): 4,
            (210, 110): 5,
            (10, 210): 6,
            (110, 210): 7,
            (210, 210): 8,
            (299, 299): 8,
            (300, 10): None,
            (10, 300): None,
            (-1, 10): None,
        }

        for (x, y), expected in checks.items():
            with self.subTest(x=x, y=y):
                self.assertEqual(gui._tile_index_from_event(SimpleNamespace(x=x, y=y)), expected)

    def test_hint_limit_is_enforced_and_button_is_disabled_after_three_hints(self):
        gui = PuzzleGUI(root=None)
        gui._puzzle.swap_tiles(0, 1)

        self.assertTrue(gui.show_hint())
        self.assertEqual(gui._hint_count, 1)
        self.assertFalse(gui._hint_limit_reached)

        gui._puzzle.swap_tiles(2, 3)
        self.assertTrue(gui.show_hint())
        self.assertEqual(gui._hint_count, 2)

        gui._puzzle.swap_tiles(4, 5)
        self.assertTrue(gui.show_hint())
        self.assertEqual(gui._hint_count, 3)
        self.assertTrue(gui._hint_limit_reached)

        gui._puzzle.swap_tiles(6, 7)
        self.assertFalse(gui.show_hint())
        self.assertEqual(gui._hint_count, 3)


if __name__ == "__main__":
    unittest.main()

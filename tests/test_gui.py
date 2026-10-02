import os
import tempfile
import unittest
from types import SimpleNamespace

import cv2
import numpy as np

from src.gui import PuzzleGUI


class DummyCanvas:
    def __init__(self, width=300, height=300):
        self._width = width
        self._height = height

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height


def write_test_image(folder, name="picture.png", size=(200, 260)):
    y, x = np.mgrid[0:size[0], 0:size[1]]
    image = np.stack([x % 256, y % 256, (x * y) % 256], axis=2).astype(np.uint8)
    path = os.path.join(folder, name)
    cv2.imwrite(path, image)
    return path


class TestGUI(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.addCleanup(self._folder.cleanup)

    def test_gui_initialises_with_default_grid_and_model_binding(self):
        gui = PuzzleGUI(root=None)

        self.assertEqual(gui.get_grid_size(), 3)
        self.assertIsNotNone(gui.get_puzzle())
        self.assertEqual(gui.get_moves(), 0)
        self.assertEqual(gui.get_incorrect_count(), 0)
        # blank board should not accept moves
        self.assertTrue(gui.get_puzzle().is_input_locked())

    def test_grid_size_update_and_model_reset(self):
        gui = PuzzleGUI(root=None)
        gui.set_grid_size(4)

        self.assertEqual(gui.get_grid_size(), 4)
        self.assertEqual(gui.get_puzzle().get_grid_size(), 4)

        gui.reset_puzzle()
        self.assertEqual(gui.get_moves(), 0)
        self.assertEqual(gui.get_incorrect_count(), 0)

        with self.assertRaises(ValueError):
            gui.set_grid_size(6)

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
            (99, 99): 0,
            (100, 100): 4,
            (300, 10): None,
            (10, 300): None,
            (-1, 10): None,
        }

        for (x, y), expected in checks.items():
            with self.subTest(x=x, y=y):
                self.assertEqual(gui._tile_index_from_event(SimpleNamespace(x=x, y=y)), expected)

    def test_click_mapping_for_four_and_five_grids(self):
        gui = PuzzleGUI(root=None)
        gui._playable_canvas = DummyCanvas(420, 420)
        for grid in (4, 5):
            gui._grid_size = grid
            tile = 420 / grid
            for index in range(grid * grid):
                row, column = divmod(index, grid)
                for dx, dy in ((1, 1), (tile - 1, tile - 1)):
                    event = SimpleNamespace(x=int(column * tile + dx), y=int(row * tile + dy))
                    with self.subTest(grid=grid, index=index, dx=dx):
                        self.assertEqual(gui._tile_index_from_event(event), index)

    def test_hint_limit_is_enforced_and_button_is_disabled_after_three_hints(self):
        gui = PuzzleGUI(root=None)
        self.assertFalse(gui.show_hint())  # no image yet
        gui.load_image(write_test_image(self._folder.name))

        for used in (1, 2, 3):
            self.assertTrue(gui.show_hint())
            self.assertEqual(gui.get_hints_remaining(), 3 - used)

        self.assertFalse(gui.show_hint())
        self.assertEqual(gui.get_hints_remaining(), 0)


if __name__ == "__main__":
    unittest.main()

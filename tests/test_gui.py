import unittest

from src.gui import PuzzleGUI


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


if __name__ == "__main__":
    unittest.main()

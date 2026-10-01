import unittest

import cv2
import numpy as np

from src.image_processor import ImageProcessor
from src.puzzle import Puzzle


class TestPuzzle(unittest.TestCase):
    def setUp(self):
        self.processor = ImageProcessor(max_size=120)

    def make_prepared_image(self, grid_size):
        board_size = grid_size * 24
        image = np.zeros((board_size, board_size, 3), dtype=np.uint8)
        for row in range(board_size):
            for column in range(board_size):
                image[row, column] = (
                    (row * 3 + column * 5) % 251,
                    (row * 7 + column * 11 + 1) % 253,
                    (row * 13 + column * 17 + 2) % 255,
                )
        return self.processor.prepare_image(image, grid_size)

    def test_constructor_and_read_methods_for_each_grid_size(self):
        for grid_size in (3, 4, 5):
            with self.subTest(grid_size=grid_size):
                original = self.make_prepared_image(grid_size)
                puzzle = Puzzle(original, grid_size)

                self.assertEqual(puzzle.get_grid_size(), grid_size)
                self.assertEqual(puzzle.get_moves(), 0)
                self.assertTrue(puzzle.is_solved())
                self.assertEqual(puzzle.get_incorrect_count(), 0)
                self.assertTrue(np.array_equal(puzzle.get_original_image(), original))
                self.assertTrue(np.array_equal(puzzle.get_current_image(), original))
                self.assertEqual(
                    [puzzle.get_tile_id(index) for index in range(grid_size ** 2)],
                    list(range(grid_size ** 2)),
                )
                self.assertTrue(all(
                    puzzle.is_tile_correct(index)
                    for index in range(grid_size ** 2)
                ))

    def test_swap_rotation_and_flip_update_board_and_count_once_each(self):
        grid_size = 3
        original = self.make_prepared_image(grid_size)
        source_tiles = self.processor.split_image(original, grid_size)
        expected_ids = list(range(grid_size ** 2))
        expected_images = [tile.copy() for tile in source_tiles]
        puzzle = Puzzle(original, grid_size)

        self.assertTrue(puzzle.swap_tiles(0, 1))
        expected_ids[0], expected_ids[1] = expected_ids[1], expected_ids[0]
        expected_images[0], expected_images[1] = expected_images[1], expected_images[0]
        self.assertEqual(puzzle.get_moves(), 1)
        self.assertEqual([puzzle.get_tile_id(i) for i in range(9)], expected_ids)

        self.assertTrue(puzzle.rotate_tile(0, 90))
        expected_images[0] = cv2.rotate(expected_images[0], cv2.ROTATE_90_CLOCKWISE)
        self.assertEqual(puzzle.get_moves(), 2)

        self.assertTrue(puzzle.flip_tile(2, "vertical"))
        expected_images[2] = cv2.flip(expected_images[2], 0)
        self.assertEqual(puzzle.get_moves(), 3)
        self.assertTrue(np.array_equal(
            puzzle.get_current_image(),
            self.processor.reassemble_image(expected_images, grid_size),
        ))
        self.assertEqual(puzzle.get_incorrect_count(), 3)
        self.assertFalse(puzzle.is_solved())

    def test_reversing_operations_restores_correctness_not_move_count(self):
        original = self.make_prepared_image(3)
        puzzle = Puzzle(original)

        puzzle.swap_tiles(0, 1)
        puzzle.swap_tiles(0, 1)
        puzzle.rotate_tile(4, 90)
        puzzle.rotate_tile(4, 270)
        puzzle.flip_tile(7, "horizontal")
        puzzle.flip_tile(7, "horizontal")

        self.assertEqual(puzzle.get_moves(), 6)
        self.assertEqual(puzzle.get_incorrect_count(), 0)
        self.assertTrue(puzzle.is_solved())
        self.assertTrue(np.array_equal(puzzle.get_current_image(), original))

    def test_self_swap_validates_index_but_does_not_count(self):
        puzzle = Puzzle(self.make_prepared_image(3))
        before = puzzle.get_current_image()

        self.assertFalse(puzzle.swap_tiles(2, 2))
        self.assertEqual(puzzle.get_moves(), 0)
        self.assertTrue(np.array_equal(puzzle.get_current_image(), before))

        with self.assertRaises(IndexError):
            puzzle.swap_tiles(9, 9)
        self.assertEqual(puzzle.get_moves(), 0)

    def test_invalid_indices_and_operations_preserve_board_and_moves(self):
        puzzle = Puzzle(self.make_prepared_image(3))
        puzzle.rotate_tile(1)
        before_image = puzzle.get_current_image()
        before_ids = [puzzle.get_tile_id(index) for index in range(9)]
        before_moves = puzzle.get_moves()

        invalid_indices = (True, False, -1, 1.5, "1", None)
        for index in invalid_indices:
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    puzzle.get_tile_id(index)
                with self.assertRaises(ValueError):
                    puzzle.is_tile_correct(index)
                with self.assertRaises(ValueError):
                    puzzle.rotate_tile(index)
                with self.assertRaises(ValueError):
                    puzzle.flip_tile(index)

        with self.assertRaises(IndexError):
            puzzle.get_tile_id(9)
        with self.assertRaises(IndexError):
            puzzle.is_tile_correct(9)

        invalid_operations = (
            lambda: puzzle.swap_tiles(0, 9),
            lambda: puzzle.rotate_tile(0, True),
            lambda: puzzle.rotate_tile(0, 45),
            lambda: puzzle.flip_tile(0, "diagonal"),
        )
        for operation in invalid_operations:
            with self.subTest(operation=operation):
                with self.assertRaises((ValueError, IndexError)):
                    operation()
                self.assertEqual(puzzle.get_moves(), before_moves)
                self.assertEqual(
                    [puzzle.get_tile_id(index) for index in range(9)], before_ids
                )
                self.assertTrue(np.array_equal(puzzle.get_current_image(), before_image))

    def test_original_and_returned_images_cannot_be_mutated_externally(self):
        original = self.make_prepared_image(3)
        puzzle = Puzzle(original)
        original_snapshot = original.copy()
        puzzle_original = puzzle.get_original_image()
        puzzle_original[:] = 0
        current_image = puzzle.get_current_image()
        current_image[:] = 255

        self.assertTrue(np.array_equal(puzzle.get_original_image(), original_snapshot))
        self.assertTrue(np.array_equal(puzzle.get_current_image(), original_snapshot))

        puzzle.swap_tiles(0, 1)
        self.assertTrue(np.array_equal(puzzle.get_original_image(), original_snapshot))

    def test_reset_restores_pixels_order_orientation_and_moves(self):
        grid_size = 4
        original = self.make_prepared_image(grid_size)
        puzzle = Puzzle(original, grid_size)

        puzzle.swap_tiles(0, 5)
        puzzle.rotate_tile(2, 90)
        puzzle.flip_tile(7, "vertical")
        puzzle.swap_tiles(10, 15)
        puzzle.rotate_tile(12, 270)
        self.assertFalse(puzzle.is_solved())

        puzzle.reset()

        self.assertEqual(puzzle.get_moves(), 0)
        self.assertTrue(puzzle.is_solved())
        self.assertEqual(puzzle.get_incorrect_count(), 0)
        self.assertEqual(
            [puzzle.get_tile_id(index) for index in range(grid_size ** 2)],
            list(range(grid_size ** 2)),
        )
        self.assertTrue(np.array_equal(puzzle.get_current_image(), original))
        self.assertTrue(np.array_equal(puzzle.get_original_image(), original))

    def test_invalid_prepared_images_and_grid_sizes_use_processor_validation(self):
        valid_image = self.make_prepared_image(3)
        for grid_size in (True, False, 2, 6, 3.0, "3", None):
            with self.subTest(grid_size=grid_size):
                with self.assertRaises(ValueError):
                    Puzzle(valid_image, grid_size)

        for image in (
            None,
            np.zeros((20, 20, 3), dtype=np.uint8),
            np.zeros((18, 21, 3), dtype=np.uint8),
            np.zeros((18, 18), dtype=np.uint8),
        ):
            with self.subTest(shape=getattr(image, "shape", None)):
                with self.assertRaises(ValueError):
                    Puzzle(image, 3)


if __name__ == "__main__":
    unittest.main()
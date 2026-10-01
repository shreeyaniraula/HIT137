import unittest

import cv2
import numpy as np

from src.tile import Tile
from src.transformations import Flip, Rotate, Swap, Transformation


class TestTransformations(unittest.TestCase):
    def make_image(self, offset=0, size=4):
        image = np.arange(size * size * 3, dtype=np.uint8).reshape(size, size, 3)
        return (image * 7 + offset) % 251

    def make_tiles(self):
        return [Tile(index, self.make_image(index * 31)) for index in range(3)]

    def assert_images_equal(self, actual_tiles, expected_images):
        for index, expected in enumerate(expected_images):
            with self.subTest(index=index):
                self.assertTrue(np.array_equal(actual_tiles[index].get_image(), expected))

    def test_transformation_is_abstract(self):
        with self.assertRaises(TypeError):
            Transformation()

    def test_target_indices_and_apply_return_values(self):
        tiles = self.make_tiles()
        operations = (
            (Swap(0, 2), (0, 2)),
            (Rotate(1), (1,)),
            (Flip(2, "vertical"), (2,)),
        )

        for operation, expected_indices in operations:
            with self.subTest(operation=type(operation).__name__):
                self.assertEqual(operation.get_target_indices(), expected_indices)
                self.assertIsNone(operation.apply(tiles))

    def test_swap_exchanges_tile_objects_and_preserves_state(self):
        tiles = self.make_tiles()
        tiles[0].rotate(90)
        expected_first_image = tiles[0].get_image()
        expected_second_image = tiles[2].get_image()
        first_object = tiles[0]
        second_object = tiles[2]

        result = Swap(0, 2).apply(tiles)

        self.assertIsNone(result)
        self.assertIs(tiles[0], second_object)
        self.assertIs(tiles[2], first_object)
        self.assertEqual((tiles[0].get_id(), tiles[2].get_id()), (2, 0))
        self.assertTrue(np.array_equal(tiles[0].get_image(), expected_second_image))
        self.assertTrue(np.array_equal(tiles[2].get_image(), expected_first_image))
        self.assertFalse(tiles[2].is_correct(2))

    def test_rotate_and_flip_delegate_to_tile(self):
        for operation, expected_operation in (
            (Rotate(1, 270), cv2.ROTATE_90_COUNTERCLOCKWISE),
        ):
            with self.subTest(operation=type(operation).__name__):
                tiles = self.make_tiles()
                before = [tile.get_image() for tile in tiles]
                result = operation.apply(tiles)
                expected = cv2.rotate(before[1], expected_operation)

                self.assertIsNone(result)
                self.assertTrue(np.array_equal(tiles[1].get_image(), expected))
                self.assertTrue(np.array_equal(tiles[0].get_image(), before[0]))
                self.assertTrue(np.array_equal(tiles[2].get_image(), before[2]))

        for direction, flip_code in (("horizontal", 1), ("vertical", 0)):
            with self.subTest(direction=direction):
                tiles = self.make_tiles()
                before = [tile.get_image() for tile in tiles]
                result = Flip(1, direction).apply(tiles)

                self.assertIsNone(result)
                self.assertTrue(np.array_equal(
                    tiles[1].get_image(), cv2.flip(before[1], flip_code)
                ))
                self.assertTrue(np.array_equal(tiles[0].get_image(), before[0]))
                self.assertTrue(np.array_equal(tiles[2].get_image(), before[2]))

    def test_polymorphic_application_of_mixed_operations(self):
        tiles = self.make_tiles()
        expected_tiles = list(tiles)
        expected_images = [tile.get_image() for tile in tiles]
        expected_tiles[0], expected_tiles[2] = expected_tiles[2], expected_tiles[0]
        expected_images[0], expected_images[2] = expected_images[2], expected_images[0]

        expected_images[1] = cv2.rotate(expected_images[1], cv2.ROTATE_180)
        expected_images[2] = cv2.flip(expected_images[2], 0)
        operations = [Swap(0, 2), Rotate(1, 180), Flip(2, "vertical")]

        for operation in operations:
            self.assertIsNone(operation.apply(tiles))

        self.assertIs(tiles[0], expected_tiles[0])
        self.assertIs(tiles[1], expected_tiles[1])
        self.assertIs(tiles[2], expected_tiles[2])
        self.assert_images_equal(tiles, expected_images)

    def test_invalid_constructors(self):
        invalid_index = (-1, True, False, 1.5, "1", None)
        for index in invalid_index:
            with self.subTest(constructor="Rotate", index=index):
                with self.assertRaises(ValueError):
                    Rotate(index)
            with self.subTest(constructor="Flip", index=index):
                with self.assertRaises(ValueError):
                    Flip(index)
            with self.subTest(constructor="Swap-first", index=index):
                with self.assertRaises(ValueError):
                    Swap(index, 1)
            with self.subTest(constructor="Swap-second", index=index):
                with self.assertRaises(ValueError):
                    Swap(0, index)

        for first_index, second_index in ((0, 0), (1, 1)):
            with self.subTest(first=first_index, second=second_index):
                with self.assertRaises(ValueError):
                    Swap(first_index, second_index)

        for angle in (True, False, 0, 45, 360, -90, 90.0, "90", None):
            with self.subTest(angle=angle):
                with self.assertRaises(ValueError):
                    Rotate(0, angle)

        for direction in ("diagonal", "Horizontal", "", None, 1):
            with self.subTest(direction=direction):
                with self.assertRaises(ValueError):
                    Flip(0, direction)

    def test_invalid_containers_indices_and_entries_do_not_mutate_board(self):
        tiles = self.make_tiles()
        before_tiles = list(tiles)
        before_images = [tile.get_image() for tile in tiles]

        with self.assertRaises(ValueError):
            Swap(0, 1).apply(tuple(tiles))
        with self.assertRaises(ValueError):
            Rotate(0).apply(None)
        with self.assertRaises(ValueError):
            Flip(0).apply("not a list")

        with self.assertRaises(IndexError):
            Swap(0, 3).apply(tiles)
        self.assertEqual(tiles, before_tiles)
        self.assert_images_equal(tiles, before_images)

        for operation in (Rotate(3), Flip(3), Swap(0, 3)):
            with self.subTest(operation=type(operation).__name__):
                with self.assertRaises(IndexError):
                    operation.apply(tiles)
                self.assertEqual(tiles, before_tiles)
                self.assert_images_equal(tiles, before_images)

        for operation in (Swap(0, 1), Rotate(1), Flip(1)):
            with self.subTest(operation=type(operation).__name__):
                invalid_tiles = list(before_tiles)
                invalid_tiles[operation.get_target_indices()[-1]] = object()
                invalid_tiles_before = list(invalid_tiles)
                before_invalid_images = [
                    tile.get_image() if isinstance(tile, Tile) else None
                    for tile in invalid_tiles
                ]

                with self.assertRaises(TypeError):
                    operation.apply(invalid_tiles)

                self.assertEqual(invalid_tiles, invalid_tiles_before)
                for index, entry in enumerate(invalid_tiles):
                    if isinstance(entry, Tile):
                        self.assertTrue(np.array_equal(
                            entry.get_image(), before_invalid_images[index]
                        ))


if __name__ == "__main__":
    unittest.main()
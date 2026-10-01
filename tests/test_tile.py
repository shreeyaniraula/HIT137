import unittest

import numpy as np

from src.image_processor import ImageProcessor
from src.tile import Tile


class TestTile(unittest.TestCase):
    def make_image(self, size=6):
        return np.arange(size * size * 3, dtype=np.uint8).reshape(size, size, 3)

    def test_identity_initial_image_and_orientation_state(self):
        image = self.make_image()
        tile = Tile(4, image)

        self.assertEqual(tile.get_id(), 4)
        self.assertTrue(np.array_equal(tile.get_image(), image))
        self.assertEqual(tile._rotation, 0)
        self.assertFalse(tile._flipped)
        self.assertFalse(np.shares_memory(tile._original_image, tile._image))

    def test_correctness_uses_home_index_and_orientation_not_pixels(self):
        tile = Tile(2, self.make_image())

        self.assertTrue(tile.is_correct(2))
        self.assertFalse(tile.is_correct(1))
        self.assertFalse(tile.is_correct(3))

        tile._image[:] = 0
        self.assertTrue(tile.is_correct(2))

        tile._rotation = 1
        self.assertFalse(tile.is_correct(2))
        tile._rotation = 0
        tile._flipped = True
        self.assertFalse(tile.is_correct(2))

    def test_constructor_and_get_image_protect_pixel_storage(self):
        source = self.make_image()
        source_before = source.copy()
        tile = Tile(0, source)

        source[:] = 255
        self.assertTrue(np.array_equal(tile.get_image(), source_before))

        returned_image = tile.get_image()
        returned_image[:] = 0
        self.assertTrue(np.array_equal(tile.get_image(), source_before))
        self.assertTrue(np.array_equal(tile._original_image, source_before))

    def test_invalid_ids_are_rejected(self):
        image = self.make_image()
        for tile_id in (-1, True, False, 1.5, "1", None):
            with self.subTest(tile_id=tile_id):
                with self.assertRaisesRegex(ValueError, "tile_id"):
                    Tile(tile_id, image)

    def test_invalid_images_are_rejected(self):
        invalid_images = (
            None,
            [],
            np.empty((0, 0, 3), dtype=np.uint8),
            np.zeros((4, 5, 3), dtype=np.uint8),
            np.zeros((4, 4), dtype=np.uint8),
            np.zeros((4, 4, 4), dtype=np.uint8),
            np.zeros((4, 4, 3), dtype=np.float32),
        )

        for image in invalid_images:
            with self.subTest(image_type=type(image).__name__,
                              shape=getattr(image, "shape", None)):
                with self.assertRaises(ValueError):
                    Tile(0, image)

    def test_correctness_rejects_invalid_indices(self):
        tile = Tile(0, self.make_image())

        for current_index in (-1, True, False, 1.5, "0", None):
            with self.subTest(current_index=current_index):
                with self.assertRaisesRegex(ValueError, "current_index"):
                    tile.is_correct(current_index)

    def test_split_image_arrays_construct_tiles_with_sequential_ids(self):
        prepared = np.arange(12 * 12 * 3, dtype=np.uint8).reshape(12, 12, 3)
        tiles = ImageProcessor().split_image(prepared, grid_size=3)
        puzzle_tiles = [Tile(tile_id, image) for tile_id, image in enumerate(tiles)]

        self.assertEqual([tile.get_id() for tile in puzzle_tiles], list(range(9)))
        for tile_id, tile in enumerate(puzzle_tiles):
            with self.subTest(tile_id=tile_id):
                self.assertTrue(np.array_equal(tile.get_image(), tiles[tile_id]))
                self.assertTrue(tile.is_correct(tile_id))


if __name__ == "__main__":
    unittest.main()
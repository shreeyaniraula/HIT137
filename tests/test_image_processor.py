import os
import tempfile
import unittest

import cv2
import numpy as np

from src.image_processor import ImageProcessor


class TestImageProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = ImageProcessor(max_size=420)

    def make_pattern_image(self, width, height):
        image = np.zeros((height, width, 3), dtype=np.uint8)
        for row_index in range(height):
            for column_index in range(width):
                image[row_index, column_index, 0] = (column_index * 17 + row_index * 13) % 256
                image[row_index, column_index, 1] = (column_index * 29 + row_index * 7) % 256
                image[row_index, column_index, 2] = (column_index * 11 + row_index * 31) % 256
        return image

    def make_regioned_image(self, grid_size, tile_size):
        board_size = grid_size * tile_size
        image = np.zeros((board_size, board_size, 3), dtype=np.uint8)

        for row_index in range(grid_size):
            for column_index in range(grid_size):
                red = (row_index * 30 + column_index * 20) % 256
                green = (row_index * 15 + column_index * 25) % 256
                blue = (row_index * 10 + column_index * 35) % 256
                value = np.array([red, green, blue], dtype=np.uint8)
                region = np.full((tile_size, tile_size, 3), value, dtype=np.uint8)
                start_y = row_index * tile_size
                end_y = start_y + tile_size
                start_x = column_index * tile_size
                end_x = start_x + tile_size
                image[start_y:end_y, start_x:end_x] = region

        return image

    def test_load_prepare_split_and_reassemble_all_formats(self):
        for extension in (".jpg", ".png", ".bmp"):
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = os.path.join(temp_dir, f"sample{extension}")
                original = self.make_pattern_image(180, 220)

                saved = cv2.imwrite(image_path, original)
                self.assertTrue(saved)

                loaded = self.processor.load_image(image_path)
                prepared = self.processor.prepare_image(loaded, grid_size=3)
                tiles = self.processor.split_image(prepared, grid_size=3)
                rebuilt = self.processor.reassemble_image(tiles, grid_size=3)

                self.assertTrue(np.array_equal(rebuilt, prepared))
                self.assertEqual(prepared.shape, (420, 420, 3))
                self.assertEqual(len(tiles), 9)

    def test_portrait_landscape_and_max_size_419(self):
        portrait = self.make_pattern_image(120, 240)
        landscape = self.make_pattern_image(240, 120)

        for image in (portrait, landscape):
            for grid_size in (3, 4, 5):
                prepared = self.processor.prepare_image(image, grid_size=grid_size)
                board_size = (420 // grid_size) * grid_size
                self.assertEqual(prepared.shape, (board_size, board_size, 3))
                self.assertEqual(prepared.shape[0] % grid_size, 0)
                self.assertEqual(prepared.shape[1] % grid_size, 0)
                self.assertLessEqual(prepared.shape[0], 420)
                self.assertLessEqual(prepared.shape[1], 420)

        small_processor = ImageProcessor(max_size=419)
        for image in (portrait, landscape):
            for grid_size in (3, 4, 5):
                prepared = small_processor.prepare_image(image, grid_size=grid_size)
                board_size = (419 // grid_size) * grid_size
                self.assertEqual(prepared.shape, (board_size, board_size, 3))
                self.assertLessEqual(prepared.shape[0], 419)
                self.assertLessEqual(prepared.shape[1], 419)
                self.assertEqual(prepared.shape[0] % grid_size, 0)
                self.assertEqual(prepared.shape[1] % grid_size, 0)

    def test_tile_ordering_and_independence(self):
        grid_size = 3
        tile_size = 12
        image = self.make_regioned_image(grid_size, tile_size)
        tiles = self.processor.split_image(image, grid_size=grid_size)

        self.assertEqual(len(tiles), 9)
        for tile_index, tile in enumerate(tiles):
            row_index = tile_index // grid_size
            column_index = tile_index % grid_size
            start_y = row_index * tile_size
            end_y = start_y + tile_size
            start_x = column_index * tile_size
            end_x = start_x + tile_size
            expected = image[start_y:end_y, start_x:end_x]
            self.assertTrue(np.array_equal(tile, expected))

        swapped = list(tiles)
        swapped[0], swapped[-1] = swapped[-1], swapped[0]
        rebuilt = self.processor.reassemble_image(swapped, grid_size=grid_size)

        self.assertTrue(np.array_equal(rebuilt[0:tile_size, 0:tile_size], tiles[-1]))
        self.assertTrue(np.array_equal(rebuilt[-tile_size:, -tile_size:], tiles[0]))

        source_tile = tiles[0].copy()
        rebuilt_copy = rebuilt.copy()
        rebuilt_copy[0, 0, :] = [99, 88, 77]
        self.assertTrue(np.array_equal(tiles[0], source_tile))
        self.assertFalse(np.array_equal(rebuilt_copy, rebuilt))

        tiles[0][0, 0] = [255, 255, 255]
        tiles[1][0, 0] = [0, 0, 0]
        self.assertFalse(np.array_equal(tiles[0], source_tile))

    def test_rgb_conversion(self):
        source = np.array([[[10, 20, 30]]], dtype=np.uint8)
        converted = self.processor.to_rgb(source)

        self.assertTrue(np.array_equal(converted, np.array([[[30, 20, 10]]], dtype=np.uint8)))
        self.assertTrue(np.array_equal(source, np.array([[[10, 20, 30]]], dtype=np.uint8)))

        rectangular = np.array([
            [[1, 2, 3], [4, 5, 6]],
            [[7, 8, 9], [10, 11, 12]],
        ], dtype=np.uint8)
        converted_rect = self.processor.to_rgb(rectangular)
        self.assertEqual(converted_rect.shape, (2, 2, 3))

    def test_failure_cases(self):
        with self.assertRaises(FileNotFoundError):
            self.processor.load_image("missing_image.png")

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = os.path.join(temp_dir, "invalid.png")
            with open(invalid_path, "wb") as handle:
                handle.write(b"not an image")

            with self.assertRaises(ValueError):
                self.processor.load_image(invalid_path)

        with self.assertRaises(ValueError):
            self.processor.prepare_image(np.zeros((20, 20, 3), dtype=np.uint8), grid_size=2)

        mismatched_tiles = [np.zeros((3, 3, 3), dtype=np.uint8)] * 8
        mismatched_tiles.append(np.zeros((2, 2, 3), dtype=np.uint8))
        with self.assertRaises(ValueError):
            self.processor.reassemble_image(mismatched_tiles, grid_size=3)

        with self.assertRaises(ValueError):
            self.processor.to_rgb(np.zeros((2, 2), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()

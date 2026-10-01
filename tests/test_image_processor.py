import os
import tempfile
import unittest

import cv2
import numpy as np

from src.image_processor import ImageProcessor


class TestImageProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = ImageProcessor(max_size=420)

    def make_solid_image(self, width, height, color=(31, 89, 157)):
        return np.full((height, width, 3), color, dtype=np.uint8)

    def make_regioned_image(self, grid_size, tile_size):
        image = np.zeros((grid_size * tile_size, grid_size * tile_size, 3), dtype=np.uint8)
        for row_index in range(grid_size):
            for column_index in range(grid_size):
                color = (row_index * 40 + column_index * 5 + 1,
                         row_index * 20 + column_index * 3 + 2,
                         row_index * 10 + column_index + 3)
                y_start = row_index * tile_size
                x_start = column_index * tile_size
                image[y_start:y_start + tile_size, x_start:x_start + tile_size] = color
        return image

    def test_load_prepare_split_and_reassemble_formats_and_grids(self):
        formats = (".jpg", ".jpeg", ".png", ".bmp", ".PNG")
        source = self.make_solid_image(180, 220)

        with tempfile.TemporaryDirectory() as temp_dir:
            for extension in formats:
                with self.subTest(extension=extension):
                    image_path = os.path.join(temp_dir, f"sample{extension}")
                    self.assertTrue(cv2.imwrite(image_path, source))
                    loaded = self.processor.load_image(image_path)
                    self.assertEqual(loaded.shape, source.shape)
                    self.assertEqual(loaded.dtype, np.uint8)
                    self.assertEqual(loaded.shape[2], 3)

                    for grid_size in (3, 4, 5):
                        with self.subTest(extension=extension, grid_size=grid_size):
                            prepared = self.processor.prepare_image(loaded, grid_size)
                            tiles = self.processor.split_image(prepared, grid_size)
                            rebuilt = self.processor.reassemble_image(tiles, grid_size)

                            self.assertEqual(len(tiles), grid_size ** 2)
                            self.assertTrue(np.array_equal(rebuilt, prepared))
                            self.assertEqual(rebuilt.dtype, np.uint8)
                            self.assertEqual(rebuilt.shape[2], 3)

        default_processor = ImageProcessor()
        default_board = default_processor.prepare_image(source)
        self.assertEqual(default_board.shape, (420, 420, 3))

    def test_prepare_content_bounds_aspect_padding_and_input_immutability(self):
        image_shapes = {
            "portrait": (120, 240),
            "landscape": (240, 120),
            "square": (150, 150),
            "tiny": (2, 3),
            "narrow_vertical": (1, 300),
            "narrow_horizontal": (300, 1),
        }
        processor = ImageProcessor(max_size=419)

        for name, (width, height) in image_shapes.items():
            for grid_size in (3, 4, 5):
                with self.subTest(image=name, grid_size=grid_size):
                    source = self.make_solid_image(width, height)
                    source_before = source.copy()
                    prepared = processor.prepare_image(source, grid_size)
                    board_size = (419 // grid_size) * grid_size

                    self.assertEqual(prepared.shape, (board_size, board_size, 3))
                    self.assertLessEqual(board_size, 419)
                    self.assertEqual(board_size % grid_size, 0)
                    self.assertEqual(prepared.dtype, np.uint8)
                    self.assertTrue(np.array_equal(source, source_before))

                    content_mask = np.any(prepared != (240, 240, 240), axis=2)
                    y_positions, x_positions = np.where(content_mask)
                    self.assertGreater(len(x_positions), 0)
                    content_height = int(y_positions.max() - y_positions.min() + 1)
                    content_width = int(x_positions.max() - x_positions.min() + 1)

                    ideal_width = board_size * width / max(width, height)
                    ideal_height = board_size * height / max(width, height)
                    self.assertLessEqual(abs(content_width - round(ideal_width)), 1)
                    self.assertLessEqual(abs(content_height - round(ideal_height)), 1)

                    top_padding = int(y_positions.min())
                    bottom_padding = board_size - 1 - int(y_positions.max())
                    left_padding = int(x_positions.min())
                    right_padding = board_size - 1 - int(x_positions.max())
                    self.assertLessEqual(abs(top_padding - bottom_padding), 1)
                    self.assertLessEqual(abs(left_padding - right_padding), 1)

                    expected_ratio = width / height
                    actual_ratio = content_width / content_height
                    rounded_ratio = (
                        max(1, round(ideal_width)) / max(1, round(ideal_height))
                    )
                    rounding_tolerance = abs(rounded_ratio - expected_ratio)
                    self.assertLessEqual(
                        abs(actual_ratio - expected_ratio),
                        rounding_tolerance + 1e-9,
                    )

    def test_split_order_and_returned_tile_storage_independence(self):
        for grid_size in (3, 4, 5):
            with self.subTest(grid_size=grid_size):
                tile_size = 4
                source = self.make_regioned_image(grid_size, tile_size)
                source_before = source.copy()
                tiles = self.processor.split_image(source, grid_size)
                self.assertEqual(len(tiles), grid_size ** 2)

                for index, tile in enumerate(tiles):
                    row_index, column_index = divmod(index, grid_size)
                    y_start = row_index * tile_size
                    x_start = column_index * tile_size
                    expected_region = source[y_start:y_start + tile_size,
                                             x_start:x_start + tile_size]
                    self.assertEqual(tile.shape, (tile_size, tile_size, 3))
                    self.assertEqual(tile.dtype, np.uint8)
                    self.assertTrue(np.array_equal(tile, expected_region))

                sibling_before = tiles[1].copy()
                tiles[0][0, 0] = (255, 254, 253)
                self.assertTrue(np.array_equal(source, source_before))
                self.assertTrue(np.array_equal(tiles[1], sibling_before))

    def test_reassembly_storage_independence_in_both_directions(self):
        for grid_size in (3, 4, 5):
            with self.subTest(grid_size=grid_size):
                tiles = self.processor.split_image(
                    self.make_regioned_image(grid_size, 4), grid_size
                )
                tile_snapshots = [tile.copy() for tile in tiles]
                rebuilt = self.processor.reassemble_image(tiles, grid_size)

                rebuilt[0, 0] = (255, 254, 253)
                self.assertTrue(all(np.array_equal(tile, before)
                                    for tile, before in zip(tiles, tile_snapshots)))

                rebuilt = self.processor.reassemble_image(tiles, grid_size)
                rebuilt_before = rebuilt.copy()
                tiles[0][0, 0] = (252, 251, 250)
                self.assertTrue(np.array_equal(rebuilt, rebuilt_before))

    def test_rgb_conversion_for_rectangular_image_and_source_immutability(self):
        rectangular = np.array([
            [[10, 20, 30], [1, 2, 3], [4, 5, 6]],
            [[7, 8, 9], [11, 12, 13], [14, 15, 16]],
        ], dtype=np.uint8)
        square = rectangular[:, :2].copy()

        for name, source in (("rectangular", rectangular), ("square", square)):
            with self.subTest(shape=name):
                source_before = source.copy()
                converted = self.processor.to_rgb(source)

                self.assertEqual(converted.shape, source.shape)
                self.assertTrue(np.array_equal(converted[0, 0], (30, 20, 10)))
                self.assertTrue(np.array_equal(converted, source[..., ::-1]))
                self.assertTrue(np.array_equal(source, source_before))

    def test_invalid_constructor_grid_and_load_inputs(self):
        for max_size in (True, False, 4, 0, -1, 4.5, "420", None):
            with self.subTest(max_size=max_size):
                with self.assertRaises(ValueError):
                    ImageProcessor(max_size)

        source = self.make_solid_image(12, 12)
        for grid_size in (True, False, 2, 6, 3.0, "3", None):
            with self.subTest(grid_size=grid_size):
                with self.assertRaises(ValueError):
                    self.processor.prepare_image(source, grid_size)
                with self.assertRaises(ValueError):
                    self.processor.split_image(source, grid_size)
                with self.assertRaises(ValueError):
                    self.processor.reassemble_image([source] * 9, grid_size)

        with tempfile.TemporaryDirectory() as temp_dir:
            for file_path in (None, "", "   "):
                with self.subTest(file_path=file_path):
                    with self.assertRaisesRegex(ValueError, "No file path"):
                        self.processor.load_image(file_path)

            missing_path = os.path.join(temp_dir, "missing.png")
            with self.assertRaises(FileNotFoundError):
                self.processor.load_image(missing_path)

            unsupported_path = os.path.join(temp_dir, "sample.gif")
            with open(unsupported_path, "wb") as handle:
                handle.write(b"not an image")
            with self.assertRaisesRegex(ValueError, "Unsupported image format"):
                self.processor.load_image(unsupported_path)

            invalid_image_path = os.path.join(temp_dir, "invalid.png")
            with open(invalid_image_path, "wb") as handle:
                handle.write(b"not an image")
            with self.assertRaisesRegex(ValueError, "not a readable image"):
                self.processor.load_image(invalid_image_path)

    def test_invalid_image_arrays_split_shapes_and_tile_lists(self):
        invalid_images = (
            None,
            [],
            np.empty((0, 3, 3), dtype=np.uint8),
            np.zeros((4, 4), dtype=np.uint8),
            np.zeros((4, 4, 4), dtype=np.uint8),
            np.zeros((4, 4, 3), dtype=np.float32),
        )
        for image in invalid_images:
            with self.subTest(image_type=type(image).__name__,
                              shape=getattr(image, "shape", None)):
                with self.assertRaises(ValueError):
                    self.processor.prepare_image(image)
                with self.assertRaises(ValueError):
                    self.processor.split_image(image)
                with self.assertRaises(ValueError):
                    self.processor.to_rgb(image)

        with self.assertRaisesRegex(ValueError, "must be square"):
            self.processor.split_image(np.zeros((12, 15, 3), dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, "divide evenly"):
            self.processor.split_image(np.zeros((10, 10, 3), dtype=np.uint8))

        valid_tile = np.zeros((4, 4, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "exactly 9"):
            self.processor.reassemble_image([valid_tile] * 8)
        mismatched_tiles = [valid_tile] * 8 + [np.zeros((3, 3, 3), dtype=np.uint8)]
        with self.assertRaisesRegex(ValueError, "same dimensions"):
            self.processor.reassemble_image(mismatched_tiles)


if __name__ == "__main__":
    unittest.main()

import unittest

import cv2
import numpy as np

from src.image_processor import ImageProcessor
from src.tile import Tile


class TestTile(unittest.TestCase):
    def make_image(self, size=6):
        image = np.arange(size * size * 3, dtype=np.uint8).reshape(size, size, 3)
        return image * 3 % 251

    def apply_rotation(self, image, angle):
        constants = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }
        return cv2.rotate(image, constants[angle])

    def apply_flip(self, image, direction):
        flip_code = 1 if direction == "horizontal" else 0
        return cv2.flip(image, flip_code)

    def orient_to_state(self, tile, reference, flipped, clockwise_turns):
        if flipped:
            tile.flip("horizontal")
            reference = self.apply_flip(reference, "horizontal")

        for _ in range(clockwise_turns):
            tile.rotate(90)
            reference = self.apply_rotation(reference, 90)

        return reference

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

    def test_supported_clockwise_rotations_match_opencv(self):
        original = self.make_image()
        rotations = ((90, cv2.ROTATE_90_CLOCKWISE),
                     (180, cv2.ROTATE_180),
                     (270, cv2.ROTATE_90_COUNTERCLOCKWISE))

        for angle, cv_rotation in rotations:
            with self.subTest(angle=angle):
                tile = Tile(0, original)
                tile.rotate(angle)
                expected = cv2.rotate(original, cv_rotation)
                self.assertTrue(np.array_equal(tile.get_image(), expected))
                self.assertFalse(tile.is_correct(0))

    def test_supported_flips_match_opencv(self):
        original = self.make_image()

        for direction, flip_code in (("horizontal", 1), ("vertical", 0)):
            with self.subTest(direction=direction):
                tile = Tile(0, original)
                tile.flip(direction)
                expected = cv2.flip(original, flip_code)
                self.assertTrue(np.array_equal(tile.get_image(), expected))
                self.assertFalse(tile.is_correct(0))

    def test_repeated_flips_and_rotations_restore_identity(self):
        original = self.make_image()

        tile = Tile(0, original)
        for _ in range(4):
            tile.rotate(90)
        self.assertTrue(np.array_equal(tile.get_image(), original))
        self.assertTrue(tile.is_correct(0))

        for direction in ("horizontal", "vertical"):
            with self.subTest(direction=direction):
                tile.reset()
                tile.flip(direction)
                tile.flip(direction)
                self.assertTrue(np.array_equal(tile.get_image(), original))
                self.assertTrue(tile.is_correct(0))

    def test_horizontal_then_vertical_flip_matches_half_turn(self):
        original = self.make_image()
        tile = Tile(0, original)
        tile.flip("horizontal")
        tile.flip("vertical")

        expected = cv2.flip(original, 1)
        expected = cv2.flip(expected, 0)
        self.assertTrue(np.array_equal(tile.get_image(), expected))
        self.assertTrue(np.array_equal(expected, cv2.rotate(original, cv2.ROTATE_180)))
        self.assertFalse(tile.is_correct(0))

    def test_all_orientation_states_accept_each_transform(self):
        original = self.make_image()

        for flipped in (False, True):
            for clockwise_turns in range(4):
                state = (flipped, clockwise_turns)
                for operation in (("rotate", 90), ("rotate", 180), ("rotate", 270),
                                  ("flip", "horizontal"), ("flip", "vertical")):
                    with self.subTest(state=state, operation=operation):
                        tile = Tile(0, original)
                        reference = self.orient_to_state(
                            tile, original.copy(), flipped, clockwise_turns
                        )

                        if operation[0] == "rotate":
                            tile.rotate(operation[1])
                            reference = self.apply_rotation(reference, operation[1])
                        else:
                            tile.flip(operation[1])
                            reference = self.apply_flip(reference, operation[1])

                        self.assertTrue(np.array_equal(tile.get_image(), reference))
                        self.assertIn(tile._rotation, (0, 1, 2, 3))
                        self.assertIsInstance(tile._flipped, bool)

    def test_mixed_transformations_match_direct_reference_operations(self):
        original = self.make_image()
        tile = Tile(0, original)
        reference = original.copy()
        operations = (
            ("rotate", 90),
            ("flip", "horizontal"),
            ("rotate", 270),
            ("flip", "vertical"),
            ("rotate", 180),
            ("flip", "horizontal"),
            ("rotate", 90),
        )
        inverse_operations = (
            ("rotate", 270),
            ("flip", "horizontal"),
            ("rotate", 180),
            ("flip", "vertical"),
            ("rotate", 90),
            ("flip", "horizontal"),
            ("rotate", 270),
        )

        for operation, value in operations:
            with self.subTest(operation=operation, value=value):
                if operation == "rotate":
                    tile.rotate(value)
                    reference = self.apply_rotation(reference, value)
                else:
                    tile.flip(value)
                    reference = self.apply_flip(reference, value)
                self.assertTrue(np.array_equal(tile.get_image(), reference))

        for operation, value in inverse_operations:
            if operation == "rotate":
                tile.rotate(value)
                reference = self.apply_rotation(reference, value)
            else:
                tile.flip(value)
                reference = self.apply_flip(reference, value)
        self.assertTrue(np.array_equal(tile.get_image(), reference))
        self.assertTrue(tile.is_correct(0))

    def test_reset_restores_pixels_identity_and_home_correctness(self):
        original = self.make_image()
        tile = Tile(3, original)
        tile.rotate(90)
        tile.flip("vertical")
        tile.rotate(270)
        self.assertFalse(tile.is_correct(3))

        tile.reset()

        self.assertEqual(tile.get_id(), 3)
        self.assertTrue(np.array_equal(tile.get_image(), original))
        self.assertTrue(tile.is_correct(3))
        self.assertFalse(tile.is_correct(2))

    def test_uniform_pixels_do_not_make_transformed_tile_correct(self):
        uniform = np.full((5, 5, 3), (25, 80, 130), dtype=np.uint8)
        tile = Tile(0, uniform)

        tile.rotate(90)

        self.assertTrue(np.array_equal(tile.get_image(), uniform))
        self.assertFalse(tile.is_correct(0))

    def test_invalid_transform_arguments_leave_tile_unchanged(self):
        original = self.make_image()
        tile = Tile(0, original)
        tile.rotate(90)
        before = tile.get_image()
        state_before = (tile._rotation, tile._flipped)

        for angle in (True, False, 0, 45, 360, -90, 90.0, "90", None):
            with self.subTest(angle=angle):
                with self.assertRaises(ValueError):
                    tile.rotate(angle)
                self.assertTrue(np.array_equal(tile.get_image(), before))
                self.assertEqual((tile._rotation, tile._flipped), state_before)
                self.assertFalse(tile.is_correct(0))

        for direction in ("diagonal", "Horizontal", "", None, 1):
            with self.subTest(direction=direction):
                with self.assertRaises(ValueError):
                    tile.flip(direction)
                self.assertTrue(np.array_equal(tile.get_image(), before))
                self.assertEqual((tile._rotation, tile._flipped), state_before)
                self.assertFalse(tile.is_correct(0))

    def test_reset_preserves_input_and_get_image_copy_protection_after_transforms(self):
        source = self.make_image()
        source_before = source.copy()
        tile = Tile(1, source)
        tile.rotate(90)
        tile.flip("vertical")

        source[:] = 0
        self.assertTrue(np.array_equal(tile._original_image, source_before))
        returned_image = tile.get_image()
        returned_image[:] = 255
        self.assertFalse(np.array_equal(tile.get_image(), returned_image))

        tile.reset()
        self.assertTrue(np.array_equal(tile.get_image(), source_before))
        self.assertTrue(tile.is_correct(1))


if __name__ == "__main__":
    unittest.main()
"""Tile class that keeps a tile's id, pixels and orientation."""

import cv2
import numpy as np


class Tile:
    """One square piece of the picture.

    Orientation is stored as a flip flag plus 0-3 clockwise quarter turns.
    """

    def __init__(self, tile_id, image):
        if isinstance(tile_id, bool) or not isinstance(tile_id, int) or tile_id < 0:
            raise ValueError("tile_id must be a non-negative integer.")

        if not isinstance(image, np.ndarray) or image.size == 0:
            raise ValueError("image must be a non-empty NumPy array.")

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image must be a three-channel array.")

        if image.dtype != np.uint8:
            raise ValueError("image must have dtype uint8.")

        if image.shape[0] != image.shape[1]:
            raise ValueError("image must be square.")

        self._tile_id = tile_id
        self._original_image = image.copy()
        self._image = image.copy()
        self._rotation = 0
        self._flipped = False

    def get_id(self):
        return self._tile_id

    def is_decoy(self):
        """Normal tiles are never decoys."""
        return False

    def get_image(self):
        return self._image.copy()

    def _refresh_image(self):
        # rebuild from the original so repeated turns do not lose quality
        image = self._original_image.copy()

        if self._flipped:
            image = cv2.flip(image, 1)

        if self._rotation == 1:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif self._rotation == 2:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif self._rotation == 3:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

        self._image = image

    def rotate(self, angle=90):
        """Rotate clockwise by 90, 180 or 270 degrees."""
        if isinstance(angle, bool) or not isinstance(angle, int) or angle not in (90, 180, 270):
            raise ValueError("angle must be 90, 180 or 270 degrees.")

        self._rotation = (self._rotation + angle // 90) % 4
        self._refresh_image()

    def flip(self, direction="horizontal"):
        """Flip horizontally or vertically."""
        if direction not in ("horizontal", "vertical"):
            raise ValueError("direction must be 'horizontal' or 'vertical'.")

        # flipping reverses the direction of any rotation already applied
        if direction == "horizontal":
            self._rotation = (-self._rotation) % 4
        else:
            self._rotation = (2 - self._rotation) % 4

        self._flipped = not self._flipped
        self._refresh_image()

    def reset(self):
        """Put the tile back to its original orientation."""
        self._rotation = 0
        self._flipped = False
        self._image = self._original_image.copy()

    def is_correct(self, current_index):
        """True if the tile is at its home index and not rotated or flipped."""
        if isinstance(current_index, bool) or not isinstance(current_index, int):
            raise ValueError("current_index must be a non-negative integer.")

        if current_index < 0:
            raise ValueError("current_index must be a non-negative integer.")

        return (
            current_index == self._tile_id
            and self._rotation == 0
            and not self._flipped
        )


class DecoyTile(Tile):
    """Fake tile for the decoy tray. It has no home so it is never correct."""

    def is_decoy(self):
        return True

    def is_correct(self, current_index):
        super().is_correct(current_index)  # still validates the index
        return False

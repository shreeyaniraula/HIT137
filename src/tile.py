"""Store a puzzle tile's identity, image pixels and orientation state."""

import cv2
import numpy as np


class Tile:
    """Represent one square BGR image tile.

    Orientation is represented as an optional horizontal flip of the original,
    followed by zero to three clockwise quarter-turns.
    """

    def __init__(self, tile_id, image):
        """Create a tile with an identity and protected image copies."""
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
        """Return this tile's original identity."""
        return self._tile_id

    def get_image(self):
        """Return a copy of this tile's current BGR image."""
        return self._image.copy()

    def _refresh_image(self):
        """Rebuild the current image from the untouched original pixels."""
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
        """Rotate the tile clockwise by 90, 180 or 270 degrees in place."""
        if isinstance(angle, bool) or not isinstance(angle, int) or angle not in (90, 180, 270):
            raise ValueError("angle must be 90, 180 or 270 degrees.")

        self._rotation = (self._rotation + angle // 90) % 4
        self._refresh_image()

    def flip(self, direction="horizontal"):
        """Flip the tile horizontally or vertically in place."""
        if direction not in ("horizontal", "vertical"):
            raise ValueError("direction must be 'horizontal' or 'vertical'.")

        # A flip reverses rotation direction under the flip-then-rotate convention.
        if direction == "horizontal":
            self._rotation = (-self._rotation) % 4
        else:
            self._rotation = (2 - self._rotation) % 4

        self._flipped = not self._flipped
        self._refresh_image()

    def reset(self):
        """Restore the original pixels and orientation without changing identity."""
        self._rotation = 0
        self._flipped = False
        self._image = self._original_image.copy()

    def is_correct(self, current_index):
        """Return whether this tile is home and has its original orientation."""
        if isinstance(current_index, bool) or not isinstance(current_index, int):
            raise ValueError("current_index must be a non-negative integer.")

        if current_index < 0:
            raise ValueError("current_index must be a non-negative integer.")

        return (
            current_index == self._tile_id
            and self._rotation == 0
            and not self._flipped
        )
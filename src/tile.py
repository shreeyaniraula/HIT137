"""Store a puzzle tile's identity, image pixels and orientation state."""

import numpy as np


class Tile:
    """Represent one square BGR image tile.

    Future orientation will be represented as an optional horizontal flip of
    the original, followed by zero to three clockwise quarter-turns. The
    transformation methods will be added in the next step.
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
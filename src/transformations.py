"""Operations that modify puzzle tiles through a shared interface."""

from abc import ABC, abstractmethod

from src.tile import Tile


class Transformation(ABC):
    """Define the common interface for operations on a tile list."""

    @abstractmethod
    def apply(self, tiles):
        """Apply this operation to the supplied tile list in place."""

    @abstractmethod
    def get_target_indices(self):
        """Return the board indices affected by this operation."""

    def _validate_targets(self, tiles):
        """Validate the list and every targeted entry before mutation."""
        if not isinstance(tiles, list):
            raise ValueError("tiles must be a list.")

        target_indices = self.get_target_indices()
        for index in target_indices:
            if index >= len(tiles):
                raise IndexError(f"Target index {index} is outside the tile list.")

        for index in target_indices:
            if not isinstance(tiles[index], Tile):
                raise TypeError(f"Target at index {index} must be a Tile.")


class Swap(Transformation):
    """Exchange two Tile objects in a board list."""

    def __init__(self, first_index, second_index):
        """Create a swap operation for two different non-negative indices."""
        for index in (first_index, second_index):
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ValueError("swap indices must be non-negative integers.")

        if first_index == second_index:
            raise ValueError("swap indices must be different.")

        self._first_index = first_index
        self._second_index = second_index

    def get_target_indices(self):
        """Return both board indices involved in the swap."""
        return (self._first_index, self._second_index)

    def apply(self, tiles):
        """Exchange the targeted Tile objects in place."""
        self._validate_targets(tiles)
        tiles[self._first_index], tiles[self._second_index] = (
            tiles[self._second_index],
            tiles[self._first_index],
        )


class Rotate(Transformation):
    """Rotate one targeted tile clockwise."""

    def __init__(self, index, angle=90):
        """Create a rotation operation for a tile index and clockwise angle."""
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")

        if isinstance(angle, bool) or not isinstance(angle, int) or angle not in (90, 180, 270):
            raise ValueError("angle must be 90, 180 or 270 degrees.")

        self._index = index
        self._angle = angle

    def get_target_indices(self):
        """Return the board index targeted by this rotation."""
        return (self._index,)

    def apply(self, tiles):
        """Rotate the targeted tile in place."""
        self._validate_targets(tiles)
        tiles[self._index].rotate(self._angle)


class Flip(Transformation):
    """Flip one targeted tile horizontally or vertically."""

    def __init__(self, index, direction="horizontal"):
        """Create a flip operation for a tile index and direction."""
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")

        if direction not in ("horizontal", "vertical"):
            raise ValueError("direction must be 'horizontal' or 'vertical'.")

        self._index = index
        self._direction = direction

    def get_target_indices(self):
        """Return the board index targeted by this flip."""
        return (self._index,)

    def apply(self, tiles):
        """Flip the targeted tile in place."""
        self._validate_targets(tiles)
        tiles[self._index].flip(self._direction)
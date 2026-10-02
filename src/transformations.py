"""Swap, rotate and flip operations that all share one base class."""

from abc import ABC, abstractmethod

from src.tile import Tile


class Transformation(ABC):
    """Base class for an operation on the tile list."""

    @abstractmethod
    def apply(self, tiles):
        """Apply the operation to the list of tiles."""

    @abstractmethod
    def get_target_indices(self):
        """Return the board indices this operation touches."""

    def _validate_targets(self, tiles):
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
    """Swap two tiles on the board."""

    def __init__(self, first_index, second_index):
        for index in (first_index, second_index):
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ValueError("swap indices must be non-negative integers.")

        if first_index == second_index:
            raise ValueError("swap indices must be different.")

        self._first_index = first_index
        self._second_index = second_index

    def get_target_indices(self):
        return (self._first_index, self._second_index)

    def apply(self, tiles):
        self._validate_targets(tiles)
        tiles[self._first_index], tiles[self._second_index] = (
            tiles[self._second_index],
            tiles[self._first_index],
        )


class Rotate(Transformation):
    """Rotate one tile clockwise."""

    def __init__(self, index, angle=90):
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")

        if isinstance(angle, bool) or not isinstance(angle, int) or angle not in (90, 180, 270):
            raise ValueError("angle must be 90, 180 or 270 degrees.")

        self._index = index
        self._angle = angle

    def get_target_indices(self):
        return (self._index,)

    def apply(self, tiles):
        self._validate_targets(tiles)
        tiles[self._index].rotate(self._angle)


class Flip(Transformation):
    """Flip one tile horizontally or vertically."""

    def __init__(self, index, direction="horizontal"):
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")

        if direction not in ("horizontal", "vertical"):
            raise ValueError("direction must be 'horizontal' or 'vertical'.")

        self._index = index
        self._direction = direction

    def get_target_indices(self):
        return (self._index,)

    def apply(self, tiles):
        self._validate_targets(tiles)
        tiles[self._index].flip(self._direction)
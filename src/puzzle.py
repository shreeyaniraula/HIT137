"""Own puzzle board state, player operations and move counting."""

from src.image_processor import ImageProcessor
from src.tile import Tile
from src.transformations import Flip, Rotate, Swap


class Puzzle:
    """Manage an ordered board of tiles created from a prepared BGR image.

    Completion does not lock operations in this model; round lifecycle controls
    will coordinate that behavior during later integration.
    """

    def __init__(self, image, grid_size=3):
        """Validate a prepared board and create its row-major tile model."""
        self._image_processor = ImageProcessor()
        tile_images = self._image_processor.split_image(image, grid_size)

        self._grid_size = grid_size
        self._original_image = image.copy()
        self._tiles = [
            Tile(tile_id, tile_image)
            for tile_id, tile_image in enumerate(tile_images)
        ]
        self._moves = 0

    def _validate_index(self, index):
        """Validate a non-negative board index and ensure it is in range."""
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")

        if index >= len(self._tiles):
            raise IndexError(f"index {index} is outside the puzzle board.")

    def get_grid_size(self):
        """Return the number of tiles along one side of the board."""
        return self._grid_size

    def get_moves(self):
        """Return the number of successful player operations."""
        return self._moves

    def get_original_image(self):
        """Return a copy of the prepared original board image."""
        return self._original_image.copy()

    def get_tile_id(self, index):
        """Return the original identity of the tile at a board index."""
        self._validate_index(index)
        return self._tiles[index].get_id()

    def is_tile_correct(self, index):
        """Return whether the tile at an index is home and correctly oriented."""
        self._validate_index(index)
        return self._tiles[index].is_correct(index)

    def get_incorrect_count(self):
        """Count tiles that are misplaced or have a changed orientation."""
        incorrect_count = 0
        for index, tile in enumerate(self._tiles):
            if not tile.is_correct(index):
                incorrect_count += 1
        return incorrect_count

    def is_solved(self):
        """Return whether every tile is in its original position and orientation."""
        return self.get_incorrect_count() == 0

    def get_current_image(self):
        """Reassemble the current tile images in their current board order."""
        tile_images = [tile.get_image() for tile in self._tiles]
        return self._image_processor.reassemble_image(tile_images, self._grid_size)

    def swap_tiles(self, first_index, second_index):
        """Swap two board tiles, returning False when both indices are equal."""
        self._validate_index(first_index)
        self._validate_index(second_index)

        if first_index == second_index:
            return False

        operation = Swap(first_index, second_index)
        operation.apply(self._tiles)
        self._moves += 1
        return True

    def rotate_tile(self, index, angle=90):
        """Rotate one tile clockwise and count the successful operation."""
        self._validate_index(index)
        operation = Rotate(index, angle)
        operation.apply(self._tiles)
        self._moves += 1
        return True

    def flip_tile(self, index, direction="horizontal"):
        """Flip one tile and count the successful operation."""
        self._validate_index(index)
        operation = Flip(index, direction)
        operation.apply(self._tiles)
        self._moves += 1
        return True

    def reset(self):
        """Restore original tile orientations, order, pixels and move count."""
        for tile in self._tiles:
            tile.reset()

        self._tiles.sort(key=lambda tile: tile.get_id())
        self._moves = 0
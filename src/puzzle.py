"""Own puzzle board state, player operations and move counting."""

import random

from src.image_processor import ImageProcessor
from src.tile import Tile
from src.transformations import Flip, Rotate, Swap


class Puzzle:
    """Manage an ordered board of tiles created from a prepared BGR image.

    The constructor creates an ordered setup board. The application must call
    scramble() before exposing a new playable round. A solved board and a locked
    round are separate states during setup. The GUI can check is_solved() after
    a successful action and display completion once; the model enforces locking.
    Member 4 can call lock_input() on timer expiry and reset() for Solve.
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
        self._scramble_summary = []
        self._input_locked = False

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

    def is_input_locked(self):
        """Return whether player operations are currently locked."""
        return self._input_locked

    def lock_input(self):
        """Lock player operations without changing board or round state."""
        self._input_locked = True

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

        if self._input_locked:
            return False

        if first_index == second_index:
            return False

        operation = Swap(first_index, second_index)
        operation.apply(self._tiles)
        self._moves += 1
        if self.is_solved():
            self._input_locked = True
        return True

    def rotate_tile(self, index, angle=90):
        """Rotate one tile clockwise and count the successful operation."""
        self._validate_index(index)
        operation = Rotate(index, angle)

        if self._input_locked:
            return False

        operation.apply(self._tiles)
        self._moves += 1
        if self.is_solved():
            self._input_locked = True
        return True

    def flip_tile(self, index, direction="horizontal"):
        """Flip one tile and count the successful operation."""
        self._validate_index(index)
        operation = Flip(index, direction)

        if self._input_locked:
            return False

        operation.apply(self._tiles)
        self._moves += 1
        if self.is_solved():
            self._input_locked = True
        return True

    def reset(self):
        """Restore original tile orientations, order, pixels and move count."""
        for tile in self._tiles:
            tile.reset()

        self._tiles.sort(key=lambda tile: tile.get_id())
        self._moves = 0
        self._scramble_summary = []
        self._input_locked = True

    def scramble(self, rng=None):
        """Create and apply a fresh randomized round with distinct tile targets."""
        if rng is None:
            selected_rng = random.Random()
        elif isinstance(rng, random.Random):
            selected_rng = rng
        else:
            raise ValueError("rng must be an instance of random.Random.")

        allocations = {
            3: (2, 2, 2),
            4: (3, 5, 4),
            5: (4, 8, 8),
        }
        swap_count, rotation_count, flip_count = allocations[self._grid_size]

        available_indices = list(range(len(self._tiles)))
        selected_rng.shuffle(available_indices)
        next_index = 0
        planned_operations = []

        for _ in range(swap_count):
            first_index = available_indices[next_index]
            second_index = available_indices[next_index + 1]
            next_index += 2
            operation = Swap(first_index, second_index)
            planned_operations.append((operation, {
                "type": "swap",
                "targets": operation.get_target_indices(),
            }))

        for _ in range(rotation_count):
            index = available_indices[next_index]
            next_index += 1
            angle = selected_rng.choice((90, 180, 270))
            operation = Rotate(index, angle)
            planned_operations.append((operation, {
                "type": "rotate",
                "targets": operation.get_target_indices(),
                "angle": angle,
            }))

        for _ in range(flip_count):
            index = available_indices[next_index]
            next_index += 1
            direction = selected_rng.choice(("horizontal", "vertical"))
            operation = Flip(index, direction)
            planned_operations.append((operation, {
                "type": "flip",
                "targets": operation.get_target_indices(),
                "direction": direction,
            }))

        selected_rng.shuffle(planned_operations)

        used_targets = set()
        for operation, _ in planned_operations:
            for index in operation.get_target_indices():
                if index in used_targets:
                    raise RuntimeError("Scramble plan contains a repeated target.")
                used_targets.add(index)

        new_tile_images = self._image_processor.split_image(
            self._original_image, self._grid_size
        )
        new_tiles = [
            Tile(tile_id, tile_image)
            for tile_id, tile_image in enumerate(new_tile_images)
        ]

        for operation, _ in planned_operations:
            operation.apply(new_tiles)

        self._tiles = new_tiles
        self._moves = 0
        self._scramble_summary = [
            record.copy() for _, record in planned_operations
        ]
        self._input_locked = False

    def get_scramble_summary(self):
        """Return a defensive copy of the latest initial scramble records."""
        return [record.copy() for record in self._scramble_summary]

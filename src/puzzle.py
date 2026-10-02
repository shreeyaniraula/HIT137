"""Puzzle model: board order, moves, scrambling and the decoy tray."""

import random

import numpy as np

from src.image_processor import ImageProcessor
from src.tile import DecoyTile, Tile
from src.transformations import Flip, Rotate, Swap


class Puzzle:
    """Holds the tiles for one image and tracks moves and the input lock.

    Call scramble() to start a round. The board locks itself once it is solved.
    """

    # (swaps, rotations, flips) for each grid size
    STANDARD_ALLOCATIONS = {
        3: (2, 2, 2),
        4: (3, 5, 4),
        5: (4, 8, 8),
    }

    def __init__(self, image, grid_size=3):
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
        self._decoy_images = []
        self._tray = []

    def _validate_index(self, index):
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")

        if index >= len(self._tiles):
            raise IndexError(f"index {index} is outside the puzzle board.")

    def get_grid_size(self):
        return self._grid_size

    def get_moves(self):
        return self._moves

    def is_input_locked(self):
        return self._input_locked

    def lock_input(self):
        """Stop any more moves, e.g. when the timer runs out."""
        self._input_locked = True

    def get_original_image(self):
        return self._original_image.copy()

    def get_tile_id(self, index):
        self._validate_index(index)
        return self._tiles[index].get_id()

    def is_tile_correct(self, index):
        self._validate_index(index)
        return self._tiles[index].is_correct(index)

    def get_incorrect_count(self):
        """Count tiles in the wrong place or orientation."""
        incorrect_count = 0
        for index, tile in enumerate(self._tiles):
            if not tile.is_correct(index):
                incorrect_count += 1
        return incorrect_count

    def is_solved(self):
        return self.get_incorrect_count() == 0

    def get_current_image(self):
        """Build the scrambled image from the tiles in their current order."""
        tile_images = [tile.get_image() for tile in self._tiles]
        return self._image_processor.reassemble_image(tile_images, self._grid_size)

    def swap_tiles(self, first_index, second_index):
        """Swap two tiles. Returns False if nothing happened."""
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
        """Rotate a tile clockwise and count the move."""
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
        """Flip a tile and count the move."""
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
        """Undo everything (used by the Solve button). Leaves the board locked."""
        all_tiles = self._tiles + self._tray
        for tile in all_tiles:
            tile.reset()

        self._tiles = sorted(
            (tile for tile in all_tiles if not tile.is_decoy()),
            key=lambda tile: tile.get_id(),
        )
        self._tray = sorted(
            (tile for tile in all_tiles if tile.is_decoy()),
            key=lambda tile: tile.get_id(),
        )
        self._moves = 0
        self._scramble_summary = []
        self._input_locked = True

    def _validate_allocation(self, allocation):
        if allocation is None:
            return self.STANDARD_ALLOCATIONS[self._grid_size]

        if not isinstance(allocation, (tuple, list)) or len(allocation) != 3:
            raise ValueError("allocation must be a (swaps, rotations, flips) tuple.")

        for count in allocation:
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError("each allocation count must be a positive integer.")

        swap_count, rotation_count, flip_count = allocation
        if swap_count * 2 + rotation_count + flip_count > len(self._tiles):
            raise ValueError("allocation targets more tiles than the board has.")

        return tuple(allocation)

    def scramble(self, rng=None, allocation=None):
        """Start a new round with random swaps, rotations and flips.

        allocation is an optional (swaps, rotations, flips) tuple used for
        difficulty levels. No tile is targeted twice.
        """
        if rng is None:
            selected_rng = random.Random()
        elif isinstance(rng, random.Random):
            selected_rng = rng
        else:
            raise ValueError("rng must be an instance of random.Random.")

        swap_count, rotation_count, flip_count = self._validate_allocation(allocation)

        # shuffle the indices and take them in order so no tile is used twice
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
        self._tray = self._build_decoy_tiles()
        self._moves = 0
        self._scramble_summary = [
            record.copy() for _, record in planned_operations
        ]
        self._input_locked = False

    def get_scramble_summary(self):
        """Return a copy of the operations used in the last scramble."""
        return [record.copy() for record in self._scramble_summary]

    def _build_decoy_tiles(self):
        first_id = len(self._tiles)
        return [
            DecoyTile(first_id + offset, image)
            for offset, image in enumerate(self._decoy_images)
        ]

    def set_decoys(self, images):
        """Set the decoy images for the tray. Call before scramble()."""
        if not isinstance(images, (list, tuple)):
            raise ValueError("images must be a list of decoy tile arrays.")

        tile_shape = self._tiles[0].get_image().shape
        for image in images:
            if not isinstance(image, np.ndarray) or image.shape != tile_shape:
                raise ValueError("each decoy must match the board tile shape.")
            if image.dtype != np.uint8:
                raise ValueError("each decoy must have dtype uint8.")

        if any(not tile.is_decoy() for tile in self._tray):
            raise RuntimeError("Cannot replace decoys while a real tile is in the tray.")

        self._decoy_images = [image.copy() for image in images]
        self._tray = self._build_decoy_tiles()

    def get_tray_size(self):
        return len(self._tray)

    def get_tray_image(self, tray_index):
        self._validate_tray_index(tray_index)
        return self._tray[tray_index].get_image()

    def is_decoy_at(self, index):
        self._validate_index(index)
        return self._tiles[index].is_decoy()

    def _validate_tray_index(self, tray_index):
        if isinstance(tray_index, bool) or not isinstance(tray_index, int) or tray_index < 0:
            raise ValueError("tray_index must be a non-negative integer.")
        if tray_index >= len(self._tray):
            raise IndexError(f"tray_index {tray_index} is outside the decoy tray.")

    def swap_with_tray(self, index, tray_index):
        """Swap a board tile with a tray tile and count the move."""
        self._validate_index(index)
        self._validate_tray_index(tray_index)

        if self._input_locked:
            return False

        self._tiles[index], self._tray[tray_index] = (
            self._tray[tray_index],
            self._tiles[index],
        )
        self._moves += 1
        if self.is_solved():
            self._input_locked = True
        return True

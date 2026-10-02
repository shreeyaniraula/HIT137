"""Extra round features: hints, difficulty levels, the timer and decoys."""

import random

import numpy as np


class Difficulty:
    """A difficulty level: how much to scramble and how long the timer is."""

    def __init__(self, name, allocations, seconds_per_tile):
        self._name = name
        self._allocations = dict(allocations)
        self._seconds_per_tile = seconds_per_tile

    def get_name(self):
        return self._name

    def get_allocation(self, grid_size):
        if grid_size not in self._allocations:
            raise ValueError("grid_size must be 3, 4 or 5.")
        return self._allocations[grid_size]

    def get_operation_count(self, grid_size):
        return sum(self.get_allocation(grid_size))

    def get_time_limit(self, grid_size):
        if grid_size not in self._allocations:
            raise ValueError("grid_size must be 3, 4 or 5.")
        return self._seconds_per_tile * grid_size * grid_size


# (swaps, rotations, flips) per grid size. Normal matches the 6/12/20 in the brief.
# A swap uses two tiles, so 2*swaps + rotations + flips must fit on the board.
DIFFICULTIES = {
    "Easy": Difficulty("Easy", {3: (1, 2, 2), 4: (2, 4, 4), 5: (3, 6, 7)}, 20),
    "Normal": Difficulty("Normal", {3: (2, 2, 2), 4: (3, 5, 4), 5: (4, 8, 8)}, 12),
    "Hard": Difficulty("Hard", {3: (2, 3, 2), 4: (3, 5, 5), 5: (4, 8, 9)}, 8),
}


def get_difficulty(name):
    if name not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {name}")
    return DIFFICULTIES[name]


class HintManager:
    """Picks hint tiles and keeps track of the 3 hint limit."""

    def __init__(self, limit=3):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer.")
        self._limit = limit
        self._used = 0
        self._markers = None

    def get_limit(self):
        return self._limit

    def get_used(self):
        return self._used

    def get_remaining(self):
        return self._limit - self._used

    def can_hint(self):
        return self._used < self._limit

    def get_markers(self):
        return self._markers

    def request(self, puzzle, rng=None):
        """Pick a random wrong tile and return (puzzle_index, home_index).

        Returns None if no hint can be given.
        """
        if not self.can_hint() or puzzle.is_input_locked():
            return None

        tile_count = puzzle.get_grid_size() ** 2
        incorrect = [i for i in range(tile_count) if not puzzle.is_tile_correct(i)]
        if not incorrect:
            return None

        chooser = rng if rng is not None else random
        index = chooser.choice(incorrect)
        # a decoy has no home, so point at the spot it is blocking
        home = index if puzzle.is_decoy_at(index) else puzzle.get_tile_id(index)

        self._used += 1
        self._markers = (index, home)
        return self._markers

    def clear_markers(self):
        self._markers = None

    def reset(self):
        self._used = 0
        self._markers = None


class CountdownTimer:
    """Countdown timer that uses Tkinter's after() to tick every second."""

    def __init__(self, scheduler, on_tick=None, on_expire=None, interval_ms=1000):
        self._scheduler = scheduler
        self._on_tick = on_tick
        self._on_expire = on_expire
        self._interval_ms = interval_ms
        self._remaining = 0
        self._job = None

    def start(self, seconds):
        """Start or restart the countdown."""
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError("seconds must be a positive integer.")
        self.cancel()
        self._remaining = seconds
        if self._on_tick is not None:
            self._on_tick(self._remaining)
        self._schedule()

    def cancel(self):
        if self._job is not None and self._scheduler is not None:
            try:
                self._scheduler.after_cancel(self._job)
            except Exception:  # window already closed
                pass
        self._job = None

    def is_running(self):
        return self._job is not None

    def get_remaining(self):
        return self._remaining

    def _schedule(self):
        if self._scheduler is not None:
            self._job = self._scheduler.after(self._interval_ms, self._tick)

    def _tick(self):
        self._job = None
        self._remaining = max(0, self._remaining - 1)
        if self._on_tick is not None:
            self._on_tick(self._remaining)
        if self._remaining == 0:
            if self._on_expire is not None:
                self._on_expire()
        else:
            self._schedule()


class DecoyFactory:
    """Makes decoy tiles by cropping the picture at half-tile offsets.

    The crops look like real pieces but do not match any tile on the board.
    """

    def __init__(self, rng=None):
        self._rng = rng if rng is not None else random.Random()

    def create(self, prepared_image, grid_size, count=None):
        """Return a list of decoy images (one per row by default)."""
        if grid_size not in (3, 4, 5):
            raise ValueError("grid_size must be 3, 4 or 5.")
        if not isinstance(prepared_image, np.ndarray) or prepared_image.ndim != 3:
            raise ValueError("prepared_image must be a three-channel NumPy array.")
        if count is None:
            count = grid_size

        tile_size = prepared_image.shape[0] // grid_size
        half = tile_size // 2
        candidates = [
            (row * tile_size + half, column * tile_size + half)
            for row in range(grid_size - 1)
            for column in range(grid_size - 1)
        ]
        self._rng.shuffle(candidates)

        # skip crops that are just the plain padding
        detailed = [
            (y, x) for y, x in candidates
            if prepared_image[y:y + tile_size, x:x + tile_size].std() > 8
        ]
        pool = detailed if len(detailed) >= count else candidates

        decoys = []
        for position in range(count):
            y, x = pool[position % len(pool)]
            crop = prepared_image[y:y + tile_size, x:x + tile_size].copy()
            crop = np.ascontiguousarray(np.rot90(crop, k=-self._rng.randrange(4)))
            decoys.append(crop)
        return decoys

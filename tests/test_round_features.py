"""Tests for hints, difficulty, the timer and decoys."""

import random
import unittest

import numpy as np

from src.image_processor import ImageProcessor
from src.puzzle import Puzzle
from src.round_features import (
    DIFFICULTIES,
    CountdownTimer,
    DecoyFactory,
    HintManager,
    get_difficulty,
)
from src.tile import DecoyTile, Tile


def make_board(grid_size=3, board=60):
    """Small test board where every pixel is different."""
    y, x = np.mgrid[0:board, 0:board]
    image = np.stack([(x * 4) % 256, (y * 4) % 256, (x + y) % 256], axis=2).astype(np.uint8)
    return ImageProcessor(max_size=board).prepare_image(image, grid_size)


class FakeScheduler:
    """Fake version of Tk after() so the timer can be stepped by hand."""

    def __init__(self):
        self.jobs = {}
        self._next = 0

    def after(self, _ms, callback):
        self._next += 1
        self.jobs[self._next] = callback
        return self._next

    def after_cancel(self, job):
        self.jobs.pop(job, None)

    def run_next(self):
        job = min(self.jobs)
        self.jobs.pop(job)()


class TestDifficulty(unittest.TestCase):
    def test_counts_scale_with_grid_and_never_reuse_a_tile(self):
        for name, level in DIFFICULTIES.items():
            counts = [level.get_operation_count(g) for g in (3, 4, 5)]
            with self.subTest(level=name):
                self.assertLess(counts[0], counts[1])
                self.assertLess(counts[1], counts[2])
                for grid in (3, 4, 5):
                    swaps, rotations, flips = level.get_allocation(grid)
                    self.assertGreaterEqual(min(swaps, rotations, flips), 1)
                    self.assertLessEqual(2 * swaps + rotations + flips, grid * grid)

    def test_levels_are_ordered_and_normal_matches_brief(self):
        for grid, expected in ((3, 6), (4, 12), (5, 20)):
            easy, normal, hard = (DIFFICULTIES[n].get_operation_count(grid) for n in ("Easy", "Normal", "Hard"))
            self.assertEqual(normal, expected)
            self.assertLess(easy, normal)
            self.assertGreater(hard, normal)
            self.assertGreater(DIFFICULTIES["Easy"].get_time_limit(grid), DIFFICULTIES["Hard"].get_time_limit(grid))

    def test_unknown_difficulty_and_grid_raise(self):
        with self.assertRaises(ValueError):
            get_difficulty("Impossible")
        with self.assertRaises(ValueError):
            get_difficulty("Easy").get_allocation(6)

    def test_puzzle_scramble_uses_difficulty_allocation(self):
        for name, level in DIFFICULTIES.items():
            for grid in (3, 4, 5):
                with self.subTest(level=name, grid=grid):
                    puzzle = Puzzle(make_board(grid), grid)
                    puzzle.scramble(random.Random(grid), allocation=level.get_allocation(grid))
                    summary = puzzle.get_scramble_summary()
                    counts = tuple(sum(r["type"] == t for r in summary) for t in ("swap", "rotate", "flip"))
                    self.assertEqual(counts, level.get_allocation(grid))
                    targets = [t for r in summary for t in r["targets"]]
                    self.assertEqual(len(targets), len(set(targets)))

    def test_invalid_allocation_leaves_round_unchanged(self):
        puzzle = Puzzle(make_board(3), 3)
        puzzle.scramble(random.Random(5))
        before = puzzle.get_current_image()
        for bad in ((0, 2, 2), (5, 0, 0), (4, 1, 1), "abc", (1, 2), (True, 1, 1)):
            with self.subTest(allocation=bad), self.assertRaises(ValueError):
                puzzle.scramble(random.Random(1), allocation=bad)
        np.testing.assert_array_equal(puzzle.get_current_image(), before)


class TestHintManager(unittest.TestCase):
    def test_hint_marks_incorrect_tile_and_its_home(self):
        puzzle = Puzzle(make_board(3), 3)
        puzzle.scramble(random.Random(7))
        hints = HintManager()
        index, home = hints.request(puzzle, random.Random(1))
        self.assertFalse(puzzle.is_tile_correct(index))
        self.assertEqual(home, puzzle.get_tile_id(index))
        self.assertEqual(hints.get_markers(), (index, home))

    def test_limit_of_three_and_reset(self):
        puzzle = Puzzle(make_board(3), 3)
        puzzle.scramble(random.Random(8))
        hints = HintManager(limit=3)
        for used in range(1, 4):
            self.assertIsNotNone(hints.request(puzzle))
            self.assertEqual(hints.get_used(), used)
        self.assertFalse(hints.can_hint())
        self.assertIsNone(hints.request(puzzle))
        self.assertEqual(hints.get_used(), 3)
        hints.reset()
        self.assertEqual(hints.get_remaining(), 3)
        self.assertIsNone(hints.get_markers())

    def test_no_hint_used_when_locked_or_solved(self):
        puzzle = Puzzle(make_board(3), 3)
        puzzle.scramble(random.Random(9))
        puzzle.lock_input()
        hints = HintManager()
        self.assertIsNone(hints.request(puzzle))
        puzzle.reset()
        self.assertIsNone(hints.request(puzzle))
        self.assertEqual(hints.get_used(), 0)

    def test_clear_markers_keeps_count(self):
        puzzle = Puzzle(make_board(3), 3)
        puzzle.scramble(random.Random(10))
        hints = HintManager()
        hints.request(puzzle)
        hints.clear_markers()
        self.assertIsNone(hints.get_markers())
        self.assertEqual(hints.get_used(), 1)

    def test_invalid_limit(self):
        for bad in (-1, 2.5, True):
            with self.subTest(limit=bad), self.assertRaises(ValueError):
                HintManager(limit=bad)


class TestCountdownTimer(unittest.TestCase):
    def test_ticks_down_then_expires_once(self):
        scheduler = FakeScheduler()
        ticks, expired = [], []
        timer = CountdownTimer(scheduler, ticks.append, lambda: expired.append(True))
        timer.start(3)
        while scheduler.jobs:
            scheduler.run_next()
        self.assertEqual(ticks, [3, 2, 1, 0])
        self.assertEqual(expired, [True])
        self.assertFalse(timer.is_running())

    def test_cancel_and_restart_drop_old_callbacks(self):
        scheduler = FakeScheduler()
        expired = []
        timer = CountdownTimer(scheduler, on_expire=lambda: expired.append(True))
        timer.start(5)
        timer.start(2)
        self.assertEqual(len(scheduler.jobs), 1)
        timer.cancel()
        self.assertEqual(scheduler.jobs, {})
        self.assertFalse(timer.is_running())
        self.assertEqual(expired, [])

    def test_invalid_seconds(self):
        timer = CountdownTimer(FakeScheduler())
        for bad in (0, -5, 1.5, True):
            with self.subTest(seconds=bad), self.assertRaises(ValueError):
                timer.start(bad)


class TestDecoys(unittest.TestCase):
    def test_decoy_tile_is_polymorphic_tile_that_is_never_correct(self):
        image = np.zeros((10, 10, 3), dtype=np.uint8)
        decoy = DecoyTile(9, image)
        self.assertIsInstance(decoy, Tile)
        self.assertTrue(decoy.is_decoy())
        self.assertFalse(Tile(0, image).is_decoy())
        self.assertFalse(decoy.is_correct(9))
        with self.assertRaises(ValueError):
            decoy.is_correct(-1)

    def test_factory_makes_tile_sized_crops_that_match_no_real_tile(self):
        for grid in (3, 4, 5):
            board = make_board(grid)
            decoys = DecoyFactory(random.Random(grid)).create(board, grid)
            tiles = ImageProcessor(max_size=60).split_image(board, grid)
            with self.subTest(grid=grid):
                self.assertEqual(len(decoys), grid)
                for decoy in decoys:
                    self.assertEqual(decoy.shape, tiles[0].shape)
                    for tile in tiles:
                        for k in range(4):
                            self.assertFalse(np.array_equal(decoy, np.rot90(tile, k)))

    def test_tray_swaps_count_moves_and_block_completion(self):
        board = make_board(3)
        puzzle = Puzzle(board, 3)
        puzzle.set_decoys(DecoyFactory(random.Random(1)).create(board, 3))
        self.assertEqual(puzzle.get_tray_size(), 3)

        self.assertTrue(puzzle.swap_with_tray(4, 0))
        self.assertTrue(puzzle.is_decoy_at(4))
        self.assertEqual(puzzle.get_moves(), 1)
        self.assertEqual(puzzle.get_incorrect_count(), 1)
        self.assertFalse(puzzle.is_solved())

        self.assertTrue(puzzle.swap_with_tray(4, 0))
        self.assertTrue(puzzle.is_solved())
        self.assertTrue(puzzle.is_input_locked())
        self.assertFalse(puzzle.swap_with_tray(4, 0))

    def test_reset_returns_real_tiles_from_tray(self):
        board = make_board(3)
        puzzle = Puzzle(board, 3)
        puzzle.set_decoys(DecoyFactory(random.Random(3)).create(board, 3))
        puzzle.scramble(random.Random(4))
        puzzle.swap_with_tray(0, 1)
        puzzle.swap_with_tray(5, 2)
        puzzle.reset()
        self.assertTrue(puzzle.is_solved())
        self.assertEqual(puzzle.get_tray_size(), 3)
        np.testing.assert_array_equal(puzzle.get_current_image(), board)

    def test_hint_on_board_decoy_points_at_blocked_position(self):
        board = make_board(3)
        puzzle = Puzzle(board, 3)
        puzzle.set_decoys(DecoyFactory(random.Random(5)).create(board, 3))
        puzzle.swap_with_tray(2, 0)
        self.assertEqual(HintManager().request(puzzle), (2, 2))

    def test_set_decoys_validation(self):
        puzzle = Puzzle(make_board(3), 3)
        with self.assertRaises(ValueError):
            puzzle.set_decoys([np.zeros((5, 5, 3), dtype=np.uint8)])
        with self.assertRaises(ValueError):
            puzzle.set_decoys("nope")
        with self.assertRaises(IndexError):
            puzzle.swap_with_tray(0, 0)


if __name__ == "__main__":
    unittest.main()

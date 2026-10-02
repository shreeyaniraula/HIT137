"""Full game tests that drive the GUI the same way the mouse does."""

import os
import random
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

from src.gui import PuzzleGUI
from src.round_features import DIFFICULTIES


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


def write_image(folder, name, height=240, width=320):
    rng = np.random.default_rng(len(name) + height)
    y, x = np.mgrid[0:height, 0:width]
    image = np.stack([x % 256, y % 256, (x * 3 + y * 5) % 256], axis=2).astype(np.uint8)
    image = cv2.add(image, rng.integers(0, 40, image.shape, dtype=np.uint8))
    path = os.path.join(folder, name)
    cv2.imwrite(path, image)
    return path


def undo_scramble_like_a_player(gui):
    """Undo the scramble using normal moves. Returns how many moves it took."""
    moves = 0
    for record in gui.get_puzzle().get_scramble_summary():
        targets = record["targets"]
        if record["type"] == "swap":
            gui.click_tile(targets[0])
            gui.click_tile(targets[1])
            moves += 1
        elif record["type"] == "rotate":
            for _ in range((360 - record["angle"]) // 90):
                gui.rotate_tile(targets[0])
                moves += 1
        else:
            gui.flip_tile(targets[0])
            moves += 1
            if record["direction"] == "vertical":
                gui.rotate_tile(targets[0])  # h-flip + 180 = v-flip
                gui.rotate_tile(targets[0])
                moves += 2
    return moves


class IntegrationBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.folder = self._tmp.name
        self.scheduler = FakeScheduler()
        self.gui = PuzzleGUI(root=None, rng=random.Random(42), scheduler=self.scheduler)

    def image(self, name="photo.png", **size):
        return write_image(self.folder, name, **size)

    def infos(self, title):
        return [m for m in self.gui.get_messages() if m[0] == "info" and m[1] == title]


class TestLoadingAndScrambling(IntegrationBase):
    def test_every_format_and_grid_starts_a_scrambled_round(self):
        shapes = {"wide.jpg": (180, 400), "tall.png": (400, 180), "square.bmp": (300, 300), "upper.JPEG": (50, 70)}
        for name, (h, w) in shapes.items():
            path = self.image(name, height=h, width=w)
            for grid in (3, 4, 5):
                with self.subTest(file=name, grid=grid):
                    self.gui.set_grid_size(grid)
                    self.assertTrue(self.gui.load_image(path))
                    puzzle = self.gui.get_puzzle()
                    self.assertEqual(puzzle.get_grid_size(), grid)
                    self.assertEqual(puzzle.get_original_image().shape[0] % grid, 0)
                    self.assertEqual(self.gui.get_moves(), 0)
                    self.assertGreater(self.gui.get_incorrect_count(), 0)
                    self.assertFalse(puzzle.is_input_locked())
                    self.assertEqual(len(puzzle.get_scramble_summary()), {3: 6, 4: 12, 5: 20}[grid])

    def test_bad_inputs_show_errors_and_keep_the_current_round(self):
        self.gui.load_image(self.image())
        self.gui.click_tile(0)
        self.gui.click_tile(1)
        before = (self.gui.get_moves(), self.gui.get_incorrect_count())

        text_as_png = os.path.join(self.folder, "fake.png")
        with open(text_as_png, "w") as handle:
            handle.write("not an image")
        pdf = os.path.join(self.folder, "notes.pdf")
        with open(pdf, "w") as handle:
            handle.write("%PDF")

        for bad in (text_as_png, pdf, os.path.join(self.folder, "missing.jpg")):
            with self.subTest(path=bad):
                self.assertFalse(self.gui.load_image(bad))
                self.assertEqual(self.gui.get_messages()[-1][0], "error")
                self.assertEqual((self.gui.get_moves(), self.gui.get_incorrect_count()), before)

        errors = len(self.gui.get_messages())
        self.assertFalse(self.gui.load_image(""))  # cancelled dialog
        self.assertEqual(len(self.gui.get_messages()), errors)

    def test_new_image_fully_resets_the_round(self):
        self.gui.set_timed(True)
        self.gui.load_image(self.image("a.png"))
        self.gui.show_hint()
        self.gui.click_tile(0)
        self.gui.rotate_tile(3)
        self.scheduler.run_next()

        self.gui.load_image(self.image("b.jpg"))
        self.assertEqual(self.gui.get_moves(), 0)
        self.assertEqual(self.gui.get_hints_remaining(), 3)
        self.assertIsNone(self.gui.get_hint_markers())
        self.assertIsNone(self.gui.get_selected_tile())
        self.assertEqual(self.gui.get_time_remaining(), DIFFICULTIES["Normal"].get_time_limit(3))
        self.assertEqual(len(self.scheduler.jobs), 1)  # old timer was cancelled

    def test_grid_and_difficulty_changes_restart_with_loaded_image(self):
        self.gui.load_image(self.image())
        self.gui.set_grid_size(5)
        self.assertEqual(self.gui.get_puzzle().get_grid_size(), 5)
        self.assertEqual(len(self.gui.get_puzzle().get_scramble_summary()), 20)
        for name, level in DIFFICULTIES.items():
            self.gui.set_difficulty(name)
            with self.subTest(level=name):
                self.assertEqual(len(self.gui.get_puzzle().get_scramble_summary()), level.get_operation_count(5))


class TestGameplay(IntegrationBase):
    def test_select_deselect_and_swap_rules(self):
        self.gui.load_image(self.image())
        self.gui.click_tile(2)
        self.assertEqual(self.gui.get_selected_tile(), 2)
        self.gui.click_tile(2)
        self.assertIsNone(self.gui.get_selected_tile())
        self.assertEqual(self.gui.get_moves(), 0)

        first_id = self.gui.get_puzzle().get_tile_id(2)
        self.gui.click_tile(2)
        self.gui.click_tile(7)
        self.assertEqual(self.gui.get_puzzle().get_tile_id(7), first_id)
        self.assertIsNone(self.gui.get_selected_tile())
        self.assertEqual(self.gui.get_moves(), 1)

        self.gui.rotate_tile(0)
        self.gui.flip_tile(0)
        self.assertEqual(self.gui.get_moves(), 3)

    def test_every_grid_is_playable_to_completion_then_locked(self):
        for grid in (3, 4, 5):
            with self.subTest(grid=grid):
                self.gui.set_grid_size(grid)
                self.gui.load_image(self.image(f"g{grid}.png"))
                expected_moves = undo_scramble_like_a_player(self.gui)

                self.assertTrue(self.gui.get_puzzle().is_solved())
                self.assertEqual(self.gui.get_incorrect_count(), 0)
                self.assertEqual(self.gui.get_moves(), expected_moves)
                self.assertEqual(len(self.infos("Puzzle complete")), grid - 2)

                # board should be locked now
                self.gui.click_tile(0)
                self.assertFalse(self.gui.rotate_tile(0))
                self.assertFalse(self.gui.flip_tile(1))
                self.assertIsNone(self.gui.get_selected_tile())
                self.assertEqual(self.gui.get_moves(), expected_moves)
                self.assertFalse(self.gui.show_hint())

    def test_hint_markers_survive_selection_but_clear_after_a_move(self):
        self.gui.load_image(self.image())
        self.assertTrue(self.gui.show_hint())
        index, home = self.gui.get_hint_markers()
        puzzle = self.gui.get_puzzle()
        self.assertFalse(puzzle.is_tile_correct(index))
        self.assertEqual(home, puzzle.get_tile_id(index))

        self.gui.click_tile(0)
        self.gui.click_tile(0)
        self.assertIsNotNone(self.gui.get_hint_markers())
        self.gui.rotate_tile(0)
        self.assertIsNone(self.gui.get_hint_markers())
        self.assertEqual(self.gui.get_hints_remaining(), 2)

    def test_solve_after_moves_restores_everything_and_clears_counters(self):
        self.gui.load_image(self.image())
        self.gui.show_hint()
        for index in (0, 4, 8):
            self.gui.rotate_tile(index)
        self.gui.click_tile(1)
        self.assertTrue(self.gui.solve_puzzle())

        puzzle = self.gui.get_puzzle()
        self.assertTrue(puzzle.is_solved())
        self.assertEqual(self.gui.get_moves(), 0)
        self.assertEqual(self.gui.get_incorrect_count(), 0)
        np.testing.assert_array_equal(puzzle.get_current_image(), puzzle.get_original_image())
        self.assertIsNone(self.gui.get_selected_tile())
        self.assertIsNone(self.gui.get_hint_markers())
        self.assertEqual(self.infos("Puzzle complete"), [])
        self.assertFalse(self.gui.rotate_tile(0))

        self.assertTrue(self.gui.scramble_round())
        self.assertFalse(self.gui.get_puzzle().is_input_locked())


class TestTimer(IntegrationBase):
    def test_time_up_locks_input_but_solve_and_new_round_still_work(self):
        self.gui.set_difficulty("Hard")
        self.gui.set_timed(True)
        self.gui.load_image(self.image())
        limit = DIFFICULTIES["Hard"].get_time_limit(3)
        self.assertEqual(self.gui.get_time_remaining(), limit)

        for _ in range(limit):
            self.scheduler.run_next()
        self.assertTrue(self.gui.get_puzzle().is_input_locked())
        self.assertEqual(len(self.infos("Time's up")), 1)
        self.assertFalse(self.gui.rotate_tile(0))
        self.assertFalse(self.gui.show_hint())

        self.assertTrue(self.gui.solve_puzzle())
        self.assertEqual(self.gui.get_incorrect_count(), 0)
        self.gui.scramble_round()
        self.assertTrue(self.gui.is_timer_running())

    def test_completion_stops_timer_and_toggle_off_cancels(self):
        self.gui.set_timed(True)
        self.gui.load_image(self.image())
        undo_scramble_like_a_player(self.gui)
        self.assertFalse(self.gui.is_timer_running())
        self.assertEqual(self.scheduler.jobs, {})

        self.gui.scramble_round()
        self.assertTrue(self.gui.is_timer_running())
        self.gui.set_timed(False)
        self.assertFalse(self.gui.is_timer_running())
        self.assertEqual(self.scheduler.jobs, {})


class TestDecoyMode(IntegrationBase):
    def test_decoys_must_be_returned_to_the_tray_to_finish(self):
        self.gui.set_decoys_enabled(True)
        self.gui.load_image(self.image())
        puzzle = self.gui.get_puzzle()
        self.assertEqual(puzzle.get_tray_size(), 3)

        undo_scramble_like_a_player(self.gui)
        self.assertTrue(puzzle.is_solved())
        self.gui.scramble_round()

        # move a decoy onto the board and back again
        self.gui.click_tray(0)
        self.gui.click_tile(4)
        self.assertTrue(self.gui.get_puzzle().is_decoy_at(4))
        self.assertEqual(self.gui.get_moves(), 1)
        markers_ok = self.gui.show_hint()
        self.assertTrue(markers_ok)

        self.gui.click_tile(4)
        self.gui.click_tray(0)
        self.assertFalse(self.gui.get_puzzle().is_decoy_at(4))
        self.assertEqual(self.gui.get_moves(), 2)

    def test_decoy_toggle_off_removes_tray(self):
        self.gui.set_decoys_enabled(True)
        self.gui.load_image(self.image())
        self.gui.set_decoys_enabled(False)
        self.assertEqual(self.gui.get_puzzle().get_tray_size(), 0)


class TestRealWindow(unittest.TestCase):
    """Uses a real Tk window, skipped if there is no display."""

    def setUp(self):
        import tkinter as tk

        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"No display available: {exc}")
        self.addCleanup(self.root.destroy)
        patcher = mock.patch("src.gui.messagebox")
        self.messagebox = patcher.start()
        self.addCleanup(patcher.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.gui = PuzzleGUI(self.root, rng=random.Random(3))
        self.gui.load_image(write_image(self._tmp.name, "real.png"))
        self.root.update()

    def click(self, sequence, x, y):
        canvas = self.gui._playable_canvas
        canvas.event_generate(sequence, x=x, y=y)
        self.root.update()

    def test_mouse_bindings_map_to_tiles(self):
        tile = 420 // 3
        self.click("<Button-1>", tile + 5, 5)
        self.assertEqual(self.gui.get_selected_tile(), 1)
        self.click("<Button-1>", tile + 5, 5)
        self.assertIsNone(self.gui.get_selected_tile())

        self.click("<Button-3>", 2 * tile + 5, 2 * tile + 5)
        self.assertEqual(self.gui.get_moves(), 1)

        self.click("<Shift-Button-1>", 5, 5)
        self.assertEqual(self.gui.get_moves(), 2)
        self.assertIsNone(self.gui.get_selected_tile())  # shift-click should not select

    def test_reference_image_ignores_clicks(self):
        self.gui._reference_canvas.event_generate("<Button-1>", x=10, y=10)
        self.gui._reference_canvas.event_generate("<Button-3>", x=10, y=10)
        self.root.update()
        self.assertEqual(self.gui.get_moves(), 0)
        self.assertIsNone(self.gui.get_selected_tile())

    def test_bad_file_shows_message_box(self):
        self.assertFalse(self.gui.load_image(os.path.join(self._tmp.name, "nope.bmp")))
        self.messagebox.showerror.assert_called_once()

    def test_completion_shows_message_box(self):
        undo_scramble_like_a_player(self.gui)
        self.root.update()
        self.messagebox.showinfo.assert_called_once()
        self.assertEqual(self.messagebox.showinfo.call_args[0][0], "Puzzle complete")


if __name__ == "__main__":
    unittest.main()

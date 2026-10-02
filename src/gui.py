"""Tkinter-based desktop interface for the image puzzle game."""

from __future__ import annotations

import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

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


class PuzzleGUI:
    """Main game window.

    root=None runs it without any widgets, which the tests use.
    """

    HINT_COLOUR = "#1a73e8"
    SELECT_COLOUR = "#f2a900"
    TICK_COLOUR = "#13a652"
    GRID_COLOUR = "#e6ecf0"
    TRAY_SLOT_SIZE = 84

    def __init__(self, root=None, max_size=420, rng=None, scheduler=None):
        self._root = root
        self._processor = ImageProcessor(max_size=max_size)
        self._board_px = (max_size // 60) * 60  # works for 3, 4 and 5
        self._rng = rng if rng is not None else random.Random()
        self._grid_size = 3
        self._difficulty = get_difficulty("Normal")
        self._timed = False
        self._decoys_enabled = False

        self._source_image = None  # original file, kept for grid changes
        self._image = None
        self._image_name = None
        self._puzzle = None
        self._selected_tile = None
        self._selected_tray = None
        self._completion_notified = False
        self._hints = HintManager(limit=3)
        self._decoy_factory = DecoyFactory(self._rng)
        self._messages = []  # popups shown, used by the tests

        self._timer = CountdownTimer(
            scheduler if scheduler is not None else root,
            on_tick=self._on_timer_tick,
            on_expire=self._on_time_up,
        )

        self._status_var = None
        self._moves_var = None
        self._incorrect_var = None
        self._timer_var = None
        self._hint_button = None
        self._grid_var = None
        self._reference_canvas = None
        self._playable_canvas = None
        self._tray_canvas = None
        self._tray_panel = None
        self._reference_photo = None
        self._playable_photo = None
        self._tray_photos = []

        self._show_placeholder()

        if self._root is not None:
            self._root.title("Image Puzzle Game")
            self._root.protocol("WM_DELETE_WINDOW", self.close)
            self._configure_widgets()
            self.refresh_display()


    def _make_blank_board(self, grid_size):
        board_size = grid_size * 24
        blank_image = np.zeros((board_size, board_size, 3), dtype=np.uint8)
        blank_image[:] = (220, 220, 220)
        return blank_image

    def _show_placeholder(self):
        # grey board shown before an image is loaded
        blank = self._processor.prepare_image(self._make_blank_board(self._grid_size), self._grid_size)
        self._puzzle = Puzzle(blank, self._grid_size)
        self._puzzle.lock_input()
        self._clear_round_state()

    def _configure_widgets(self):
        self._status_var = tk.StringVar(value="Choose a grid size, then load an image to begin.")
        self._moves_var = tk.StringVar(value="0")
        self._incorrect_var = tk.StringVar(value="0")
        self._timer_var = tk.StringVar(value="Off")

        toolbar = ttk.Frame(self._root, padding=(12, 10, 12, 4))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Load image", command=self.load_image).pack(side="left", padx=(0, 10))

        ttk.Label(toolbar, text="Grid:").pack(side="left", padx=(0, 4))
        self._grid_var = tk.StringVar(value=str(self._grid_size))
        grid_menu = ttk.Combobox(toolbar, width=4, textvariable=self._grid_var,
                                 values=("3", "4", "5"), state="readonly")
        grid_menu.pack(side="left")
        grid_menu.bind("<<ComboboxSelected>>", self._on_grid_change)

        ttk.Label(toolbar, text="Difficulty:").pack(side="left", padx=(12, 4))
        self._difficulty_var = tk.StringVar(value=self._difficulty.get_name())
        difficulty_menu = ttk.Combobox(toolbar, width=7, textvariable=self._difficulty_var,
                                       values=tuple(DIFFICULTIES), state="readonly")
        difficulty_menu.pack(side="left")
        difficulty_menu.bind("<<ComboboxSelected>>",
                             lambda _event: self.set_difficulty(self._difficulty_var.get()))

        self._timed_var = tk.BooleanVar(value=self._timed)
        ttk.Checkbutton(toolbar, text="Time limit", variable=self._timed_var,
                        command=lambda: self.set_timed(self._timed_var.get())).pack(side="left", padx=(12, 4))
        self._decoys_var = tk.BooleanVar(value=self._decoys_enabled)
        ttk.Checkbutton(toolbar, text="Decoys", variable=self._decoys_var,
                        command=lambda: self.set_decoys_enabled(self._decoys_var.get())).pack(side="left", padx=(4, 4))

        controls = ttk.Frame(self._root, padding=(12, 4, 12, 4))
        controls.pack(fill="x")
        ttk.Button(controls, text="New round", command=self.scramble_round).pack(side="left", padx=(0, 6))
        self._hint_button = ttk.Button(controls, text="Hint", command=self.show_hint)
        self._hint_button.pack(side="left", padx=6)
        ttk.Button(controls, text="Solve", command=self.solve_puzzle).pack(side="left", padx=6)

        info = ttk.Frame(controls)
        info.pack(side="right")
        bold = ("Segoe UI", 10, "bold")
        for label, var in (("Moves:", self._moves_var), ("Tiles left:", self._incorrect_var),
                           ("Time:", self._timer_var)):
            ttk.Label(info, text=label).pack(side="left", padx=(12, 2))
            ttk.Label(info, textvariable=var, font=bold).pack(side="left")

        board_area = ttk.Frame(self._root, padding=(12, 6, 12, 6))
        board_area.pack(fill="both", expand=True)

        reference_panel = ttk.Frame(board_area, padding=(0, 0, 12, 0))
        reference_panel.pack(side="left", anchor="n")
        ttk.Label(reference_panel, text="Original (reference)", font=("Segoe UI", 11, "bold")).pack(pady=(0, 6))
        self._reference_canvas = self._make_board_canvas(reference_panel)

        playable_panel = ttk.Frame(board_area)
        playable_panel.pack(side="left", anchor="n")
        ttk.Label(playable_panel, text="Puzzle", font=("Segoe UI", 11, "bold")).pack(pady=(0, 6))
        self._playable_canvas = self._make_board_canvas(playable_panel)
        self._playable_canvas.bind("<Button-1>", self._on_tile_click)
        self._playable_canvas.bind("<Button-3>", self._on_tile_rotate)
        self._playable_canvas.bind("<Button-2>", self._on_tile_rotate)  # right click on mac
        self._playable_canvas.bind("<Shift-Button-1>", self._on_tile_flip)

        self._tray_panel = ttk.Frame(playable_panel, padding=(0, 8, 0, 0))
        ttk.Label(self._tray_panel, text="Decoy tray: these pieces do not belong in the picture").pack(anchor="w")
        self._tray_canvas = tk.Canvas(self._tray_panel, width=self._board_px, height=self.TRAY_SLOT_SIZE,
                                      highlightthickness=0, bg="#e9eef4")
        self._tray_canvas.pack(anchor="w")
        self._tray_canvas.bind("<Button-1>", self._on_tray_click)

        status_bar = ttk.Frame(self._root, padding=(12, 0, 12, 10))
        status_bar.pack(fill="x")
        ttk.Label(status_bar, textvariable=self._status_var, wraplength=880, justify="left").pack(anchor="w")
        ttk.Label(status_bar, foreground="#5f6b75",
                  text="Left click: select / swap   Right click: rotate 90°   Shift + left click: flip").pack(anchor="w")

        self._refresh_hint_button()

    def _make_board_canvas(self, parent):
        canvas = tk.Canvas(parent, width=self._board_px, height=self._board_px,
                           highlightthickness=0, bd=0, bg="#e9eef4")
        canvas.pack()
        return canvas

    def _on_grid_change(self, _event):
        try:
            value = int(self._grid_var.get())
        except ValueError:
            return
        self.set_grid_size(value)


    def _clear_round_state(self):
        self._selected_tile = None
        self._selected_tray = None
        self._completion_notified = False
        self._hints.reset()

    def _has_image(self):
        return self._image is not None

    def _start_round(self):
        self._timer.cancel()
        puzzle = Puzzle(self._image.copy(), self._grid_size)
        if self._decoys_enabled:
            puzzle.set_decoys(self._decoy_factory.create(self._image, self._grid_size))
        puzzle.scramble(self._rng, allocation=self._difficulty.get_allocation(self._grid_size))
        self._puzzle = puzzle
        self._clear_round_state()
        if self._timed:
            self._timer.start(self._difficulty.get_time_limit(self._grid_size))
        else:
            self._set_timer_text("Off")
        self._update_tray_visibility()
        self.refresh_display()

    def _prepare_and_start(self):
        self._image = self._processor.prepare_image(self._source_image, self._grid_size)
        self._start_round()

    def load_image(self, file_path=None):
        """Load an image and start a new round."""
        if file_path is None and self._root is not None:
            file_path = filedialog.askopenfilename(
                title="Select an image",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
            )

        if not file_path:
            self._set_status("No image selected.")
            return False

        try:
            image = self._processor.load_image(file_path)
            self._source_image = image
            self._image_name = os.path.basename(file_path)
            self._prepare_and_start()
        except Exception as exc:
            self.show_error(f"Could not load the image.\n\n{exc}")
            return False

        self._set_status(
            f"Loaded {self._image_name}: {self._grid_size}x{self._grid_size} grid, "
            f"{self._difficulty.get_name()} difficulty "
            f"({self._difficulty.get_operation_count(self._grid_size)} transformations)."
        )
        return True

    def scramble_round(self):
        if not self._has_image():
            self._set_status("Load an image first.")
            return False
        self._start_round()
        self._set_status("New round started.")
        return True

    def reset_puzzle(self):
        if self._has_image():
            return self.scramble_round()
        self._timer.cancel()
        self._show_placeholder()
        self.refresh_display()
        return True

    def set_grid_size(self, grid_size):
        if isinstance(grid_size, bool) or not isinstance(grid_size, int):
            raise ValueError("grid_size must be an integer value of 3, 4 or 5.")
        if grid_size not in (3, 4, 5):
            raise ValueError("grid_size must be 3, 4 or 5.")

        self._grid_size = grid_size
        if self._grid_var is not None:
            self._grid_var.set(str(grid_size))
        if self._has_image():
            self._prepare_and_start()
            self._set_status(f"Grid changed to {grid_size}x{grid_size}. New round started.")
        else:
            self.reset_puzzle()

    def set_difficulty(self, name):
        self._difficulty = get_difficulty(name)
        if self._root is not None:
            self._difficulty_var.set(name)
        if self._has_image():
            self._start_round()
            self._set_status(f"Difficulty set to {name}. New round started.")

    def set_timed(self, enabled):
        self._timed = bool(enabled)
        if self._root is not None:
            self._timed_var.set(self._timed)
        if not self._timed:
            self._timer.cancel()
            self._set_timer_text("Off")
        elif self._has_image() and not self._puzzle.is_input_locked():
            self._timer.start(self._difficulty.get_time_limit(self._grid_size))

    def set_decoys_enabled(self, enabled):
        self._decoys_enabled = bool(enabled)
        if self._root is not None:
            self._decoys_var.set(self._decoys_enabled)
        self._update_tray_visibility()
        if self._has_image():
            self._start_round()
            self._set_status("Decoys on. New round started." if enabled else "Decoys off. New round started.")

    def solve_puzzle(self):
        """Solve button: undo all transformations and reset the counters."""
        if not self._has_image():
            self._set_status("Load an image first.")
            return False
        self._timer.cancel()
        self._puzzle.reset()
        self._selected_tile = None
        self._selected_tray = None
        self._hints.clear_markers()
        self._completion_notified = True  # no "you win" popup for Solve
        self._set_status("Puzzle solved automatically. Load an image or start a new round to play again.")
        self.refresh_display()
        return True


    def click_tile(self, index):
        """Left click: select, deselect or swap."""
        if self._puzzle.is_input_locked():
            return False

        if self._selected_tray is not None:
            tray_index = self._selected_tray
            self._selected_tray = None
            if self._puzzle.swap_with_tray(index, tray_index):
                self._after_move(f"Swapped tile {index} with tray slot {tray_index}.")
                return True
            return False

        if self._selected_tile is None:
            self._selected_tile = index
            self._set_status(f"Selected tile {index}.")
            self.refresh_display()
            return False

        if self._selected_tile == index:
            self._selected_tile = None
            self._set_status("Selection cleared.")
            self.refresh_display()
            return False

        first = self._selected_tile
        self._selected_tile = None
        if self._puzzle.swap_tiles(first, index):
            self._after_move(f"Swapped tiles {first} and {index}.")
            return True
        self.refresh_display()
        return False

    def click_tray(self, tray_index):
        if self._puzzle.is_input_locked() or tray_index >= self._puzzle.get_tray_size():
            return False

        if self._selected_tile is not None:
            board_index = self._selected_tile
            self._selected_tile = None
            if self._puzzle.swap_with_tray(board_index, tray_index):
                self._after_move(f"Swapped tile {board_index} with tray slot {tray_index}.")
                return True
            return False

        self._selected_tray = None if self._selected_tray == tray_index else tray_index
        self._set_status("Selection cleared." if self._selected_tray is None
                         else f"Selected tray slot {tray_index}. Click a puzzle tile to swap.")
        self.refresh_display()
        return False

    def rotate_tile(self, index):
        if self._puzzle.rotate_tile(index, 90):
            self._after_move(f"Rotated tile {index}.")
            return True
        return False

    def flip_tile(self, index):
        if self._puzzle.flip_tile(index, "horizontal"):
            self._after_move(f"Flipped tile {index}.")
            return True
        return False

    def _after_move(self, message):
        self._selected_tile = None
        self._selected_tray = None
        self._hints.clear_markers()  # hint goes away after a move
        self._set_status(message)
        self.refresh_display()
        self._check_completion()

    def _check_completion(self):
        if self._puzzle.is_solved() and not self._completion_notified:
            self._completion_notified = True
            self._timer.cancel()
            self.refresh_display()
            message = f"You restored the picture in {self._puzzle.get_moves()} moves"
            if self._timed:
                message += f" with {self._format_time(self._timer.get_remaining())} to spare"
            message += ".\n\nLoad another image or start a new round to keep playing."
            self._set_status("Puzzle complete!")
            self.show_info("Puzzle complete", message)


    def show_hint(self):
        if not self._has_image():
            self._set_status("Load an image first.")
            return False
        markers = self._hints.request(self._puzzle, self._rng)
        if markers is None:
            if not self._hints.can_hint():
                self._set_status("Hint limit reached for this image.")
            self._refresh_hint_button()
            return False

        index, home = markers
        if self._puzzle.is_decoy_at(index):
            self._set_status(f"Hint: tile {index} is a decoy. Swap it back to the tray.")
        else:
            self._set_status(f"Hint: the circled tile belongs at the circled spot on the original (position {home}).")
        self.refresh_display()
        return True

    def get_hint_markers(self):
        return self._hints.get_markers()

    def get_hints_remaining(self):
        return self._hints.get_remaining()

    def _on_timer_tick(self, remaining):
        self._set_timer_text(self._format_time(remaining))

    def _on_time_up(self):
        if self._puzzle.is_solved():
            return
        self._puzzle.lock_input()
        self._selected_tile = None
        self._selected_tray = None
        self._hints.clear_markers()
        self._set_status("Time's up! Press Solve to see the answer, or start a new round.")
        self.refresh_display()
        self.show_info("Time's up", "You ran out of time. The puzzle is locked.\n\n"
                                    "Press Solve, start a new round or load another image.")

    @staticmethod
    def _format_time(seconds):
        return f"{seconds // 60}:{seconds % 60:02d}"


    def get_grid_size(self):
        return self._grid_size

    def get_puzzle(self):
        return self._puzzle

    def get_difficulty_name(self):
        return self._difficulty.get_name()

    def get_moves(self):
        return self._puzzle.get_moves()

    def get_incorrect_count(self):
        return self._puzzle.get_incorrect_count()

    def get_selected_tile(self):
        return self._selected_tile

    def get_messages(self):
        return list(self._messages)

    def is_timer_running(self):
        return self._timer.is_running()

    def get_time_remaining(self):
        return self._timer.get_remaining()


    def _tile_index_from_event(self, event):
        if self._playable_canvas is None:
            return None

        board_size = self._get_canvas_board_size(self._playable_canvas)
        tile_size = board_size / self._grid_size
        if event.x < 0 or event.y < 0 or event.x >= board_size or event.y >= board_size:
            return None

        row = int(event.y // tile_size)
        column = int(event.x // tile_size)
        if row >= self._grid_size or column >= self._grid_size:
            return None
        return row * self._grid_size + column

    def _get_canvas_board_size(self, canvas):
        if canvas is None:
            return self._board_px
        size = min(canvas.winfo_width(), canvas.winfo_height())
        # Tk reports 1x1 before the window is drawn
        return size if size > 1 else self._board_px

    def _on_tile_click(self, event):
        index = self._tile_index_from_event(event)
        if index is not None:
            self.click_tile(index)

    def _on_tile_rotate(self, event):
        index = self._tile_index_from_event(event)
        if index is not None:
            self.rotate_tile(index)

    def _on_tile_flip(self, event):
        index = self._tile_index_from_event(event)
        if index is not None:
            self.flip_tile(index)
        return "break"

    def _tray_slot_size(self):
        count = max(1, self._puzzle.get_tray_size())
        return min(self.TRAY_SLOT_SIZE, self._board_px // count)

    def _on_tray_click(self, event):
        slot = self._tray_slot_size()
        if event.y < 0 or event.y >= slot or event.x < 0:
            return
        tray_index = int(event.x // slot)
        if tray_index < self._puzzle.get_tray_size():
            self.click_tray(tray_index)


    def _set_status(self, message):
        if self._status_var is not None:
            self._status_var.set(message)

    def _set_timer_text(self, text):
        if self._timer_var is not None:
            self._timer_var.set(text)

    def _update_tray_visibility(self):
        if self._tray_panel is None:
            return
        if self._decoys_enabled:
            self._tray_panel.pack(anchor="w")
        else:
            self._tray_panel.pack_forget()

    def _refresh_hint_button(self):
        if self._hint_button is None:
            return
        self._hint_button.configure(text=f"Hint ({self._hints.get_remaining()} left)")
        usable = self._has_image() and self._hints.can_hint() and not self._puzzle.is_input_locked()
        self._hint_button.configure(state="normal" if usable else "disabled")

    def refresh_display(self):
        if self._moves_var is not None:
            self._moves_var.set(str(self.get_moves()))
        if self._incorrect_var is not None:
            self._incorrect_var.set(str(self.get_incorrect_count()))
        self._refresh_hint_button()

        if self._reference_canvas is not None:
            self._draw_reference_canvas()
        if self._playable_canvas is not None:
            self._draw_playable_canvas()
        if self._tray_canvas is not None and self._decoys_enabled:
            self._draw_tray()

    def _draw_reference_canvas(self):
        canvas = self._reference_canvas
        canvas.delete("all")
        board_size = self._get_canvas_board_size(canvas)
        self._reference_photo = self._photo_for_array(self._puzzle.get_original_image(), board_size, board_size)
        canvas.create_image(0, 0, anchor="nw", image=self._reference_photo)

        markers = self._hints.get_markers()
        if markers is not None:
            self._draw_hint_marker(canvas, markers[1], self._grid_size, board_size)

    def _draw_playable_canvas(self):
        canvas = self._playable_canvas
        canvas.delete("all")
        grid_size = self._puzzle.get_grid_size()
        board_size = self._get_canvas_board_size(canvas)
        self._playable_photo = self._photo_for_array(self._puzzle.get_current_image(), board_size, board_size)
        canvas.create_image(0, 0, anchor="nw", image=self._playable_photo)
        self._draw_grid(canvas, grid_size, board_size, board_size)

        if self._has_image():
            for index in range(grid_size ** 2):
                if self._puzzle.is_tile_correct(index):
                    self._draw_correct_marker(canvas, index, grid_size, board_size)

        markers = self._hints.get_markers()
        if markers is not None:
            self._draw_hint_marker(canvas, markers[0], grid_size, board_size)

        if self._selected_tile is not None:
            self._draw_selection_outline(canvas, self._selected_tile, grid_size, board_size)

    def _draw_tray(self):
        canvas = self._tray_canvas
        canvas.delete("all")
        self._tray_photos = []
        slot = self._tray_slot_size()
        for tray_index in range(self._puzzle.get_tray_size()):
            photo = self._photo_for_array(self._puzzle.get_tray_image(tray_index), slot - 4, slot - 4)
            self._tray_photos.append(photo)
            canvas.create_image(tray_index * slot + 2, 2, anchor="nw", image=photo)
            if tray_index == self._selected_tray:
                canvas.create_rectangle(tray_index * slot + 2, 2, (tray_index + 1) * slot - 2, slot - 2,
                                        outline=self.SELECT_COLOUR, width=3)

    def _draw_grid(self, canvas, grid_size, width, height):
        tile_size = min(width, height) / grid_size
        for line in range(1, grid_size):
            offset = line * tile_size
            canvas.create_line(offset, 0, offset, height, fill=self.GRID_COLOUR, width=1)
            canvas.create_line(0, offset, width, offset, fill=self.GRID_COLOUR, width=1)

    def _draw_selection_outline(self, canvas, tile_index, grid_size, board_size):
        tile_size = board_size / grid_size
        row, column = divmod(tile_index, grid_size)
        canvas.create_rectangle(column * tile_size + 2, row * tile_size + 2,
                                (column + 1) * tile_size - 2, (row + 1) * tile_size - 2,
                                outline=self.SELECT_COLOUR, width=4)

    def _draw_hint_marker(self, canvas, tile_index, grid_size, board_size):
        tile_size = board_size / grid_size
        row, column = divmod(tile_index, grid_size)
        x = column * tile_size + tile_size / 2
        y = row * tile_size + tile_size / 2
        radius = tile_size * 0.3
        canvas.create_oval(x - radius, y - radius, x + radius, y + radius, outline=self.HINT_COLOUR, width=4)

    def _draw_correct_marker(self, canvas, tile_index, grid_size, board_size):
        tile_size = board_size / grid_size
        row, column = divmod(tile_index, grid_size)
        x = (column + 1) * tile_size - 14
        y = row * tile_size + 14
        canvas.create_oval(x - 10, y - 10, x + 10, y + 10, fill="white", outline=self.TICK_COLOUR, width=2)
        canvas.create_line(x - 5, y, x - 1, y + 5, x + 6, y - 5, fill=self.TICK_COLOUR, width=3)

    def _photo_for_array(self, image, width, height):
        if Image is None or ImageTk is None:
            return None
        pillow_image = Image.fromarray(self._processor.to_rgb(image))
        if width and height:
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            pillow_image = pillow_image.resize((width, height), resampling)
        return ImageTk.PhotoImage(pillow_image, master=self._root)


    def show_error(self, message):
        self._messages.append(("error", "Puzzle error", message))
        if self._root is not None:
            messagebox.showerror("Puzzle error", message, parent=self._root)

    def show_info(self, title, message):
        self._messages.append(("info", title, message))
        if self._root is not None:
            messagebox.showinfo(title, message, parent=self._root)

    def close(self):
        self._timer.cancel()
        if self._root is not None:
            self._root.destroy()

    def run(self):
        if self._root is not None:
            self._root.mainloop()


def main():
    root = tk.Tk()
    app = PuzzleGUI(root)
    app.run()


if __name__ == "__main__":
    main()

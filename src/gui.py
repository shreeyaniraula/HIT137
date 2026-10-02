"""Tkinter-based desktop interface for the image puzzle game."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - Pillow is optional until GUI runtime is active.
    Image = None
    ImageTk = None

import numpy as np

from src.image_processor import ImageProcessor
from src.puzzle import Puzzle


class PuzzleGUI:
    """Manage the Tkinter board, callbacks and puzzle state for Member 3."""

    def __init__(self, root=None, max_size=420):
        self._processor = ImageProcessor(max_size=max_size)
        self._grid_size = 3
        self._selected_tile = None
        self._image = None
        self._puzzle = None
        self._hint_positions = []
        self._hint_count = 0
        self._hint_limit_reached = False
        self._hint_button = None
        self._root = root

        if self._root is None:
            try:
                self._root = tk.Tk()
            except Exception:
                self._root = None

        self._selected_tile_var = None
        self._status_var = None
        self._moves_var = None
        self._incorrect_var = None
        self._reference_canvas = None
        self._playable_canvas = None
        self._reference_photo = None
        self._playable_photo = None

        self._default_image = self._make_blank_board(self._grid_size)
        self._puzzle = Puzzle(self._processor.prepare_image(self._default_image, self._grid_size), self._grid_size)

        if self._root is not None:
            self._root.title("Image Puzzle Game")
            self._root.minsize(980, 720)
            self._configure_widgets()
            self.refresh_display()

    def _make_blank_board(self, grid_size):
        board_size = grid_size * 24
        blank_image = np.zeros((board_size, board_size, 3), dtype=np.uint8)
        blank_image[:] = (220, 220, 220)
        return blank_image

    def _configure_widgets(self):
        self._status_var = tk.StringVar(value="Select an image to begin.")
        self._moves_var = tk.StringVar(value="0")
        self._incorrect_var = tk.StringVar(value="0")
        self._selected_tile_var = tk.StringVar(value="None")

        self._root.configure(bg="#edf3f8")

        toolbar = ttk.Frame(self._root, padding=(12, 10, 12, 8))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Load image", command=self.load_image).pack(side="left", padx=(0, 8))

        ttk.Label(toolbar, text="Grid:").pack(side="left", padx=(12, 6))
        self._grid_var = tk.StringVar(value=str(self._grid_size))
        grid_menu = ttk.Combobox(
            toolbar,
            width=6,
            textvariable=self._grid_var,
            values=("3", "4", "5"),
            state="readonly",
        )
        grid_menu.pack(side="left")
        grid_menu.bind("<<ComboboxSelected>>", self._on_grid_change)

        ttk.Button(toolbar, text="Scramble", command=self.scramble_round).pack(side="left", padx=(18, 6))
        ttk.Button(toolbar, text="Reset", command=self.reset_puzzle).pack(side="left", padx=(6, 6))
        self._hint_button = ttk.Button(toolbar, text="Hint", command=self.show_hint)
        self._hint_button.pack(side="left", padx=(6, 6))
        self._refresh_hint_button()

        info_bar = ttk.Frame(self._root)
        info_bar.pack(fill="x", padx=12, pady=(0, 10))

        info_frame = ttk.Frame(info_bar, padding=(10, 6, 10, 6))
        info_frame.pack(fill="x")

        ttk.Label(info_frame, text="Moves:").pack(side="left")
        ttk.Label(info_frame, textvariable=self._moves_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 18))
        ttk.Label(info_frame, text="Incorrect tiles:").pack(side="left")
        ttk.Label(info_frame, textvariable=self._incorrect_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 18))
        ttk.Label(info_frame, text="Selected:").pack(side="left")
        ttk.Label(info_frame, textvariable=self._selected_tile_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 0))

        board_area = ttk.Frame(self._root)
        board_area.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._reference_panel = ttk.Frame(board_area, padding=(0, 0, 10, 0))
        self._reference_panel.pack(side="left", fill="both", expand=True)
        ttk.Label(self._reference_panel, text="Original", font=("Segoe UI", 11, "bold")).pack(anchor="center", pady=(0, 6))
        self._reference_canvas = tk.Canvas(self._reference_panel, width=420, height=420, highlightthickness=2, highlightbackground="#d0dae3", bg="#e9eef4")
        self._reference_canvas.pack(fill="both", expand=True)
        self._reference_canvas.bind("<Button-1>", self._on_reference_click)

        self._playable_panel = ttk.Frame(board_area)
        self._playable_panel.pack(side="left", fill="both", expand=True)
        ttk.Label(self._playable_panel, text="Puzzle", font=("Segoe UI", 11, "bold")).pack(anchor="center", pady=(0, 6))
        self._playable_canvas = tk.Canvas(self._playable_panel, width=420, height=420, highlightthickness=2, highlightbackground="#d0dae3", bg="#e9eef4")
        self._playable_canvas.pack(fill="both", expand=True)
        self._playable_canvas.bind("<Button-1>", self._on_tile_click)
        self._playable_canvas.bind("<Button-3>", self._on_tile_rotate)
        self._playable_canvas.bind("<Shift-Button-1>", self._on_tile_flip)

        status_bar = ttk.Frame(self._root)
        status_bar.pack(fill="x", padx=12, pady=(0, 12))
        status_inner = ttk.Frame(status_bar, padding=(10, 8, 10, 8))
        status_inner.pack(fill="x")
        ttk.Label(status_inner, textvariable=self._status_var, wraplength=900, justify="left").pack(anchor="w")

    def _on_grid_change(self, event):
        try:
            value = int(self._grid_var.get())
        except ValueError:
            return
        self.set_grid_size(value)

    def _refresh_hint_button(self):
        if self._hint_button is None:
            return
        if self._hint_limit_reached or self._puzzle is None:
            self._hint_button.configure(state="disabled")
        else:
            self._hint_button.configure(state="normal")

    def set_grid_size(self, grid_size):
        if isinstance(grid_size, bool) or not isinstance(grid_size, int):
            raise ValueError("grid_size must be an integer value of 3, 4 or 5.")
        if grid_size not in (3, 4, 5):
            raise ValueError("grid_size must be 3, 4 or 5.")

        self._grid_size = grid_size
        self._hint_count = 0
        self._hint_limit_reached = False
        self._hint_positions = []
        self._refresh_hint_button()
        self.reset_puzzle()
        if self._root is not None and self._grid_var is not None:
            self._grid_var.set(str(grid_size))

    def get_grid_size(self):
        return self._grid_size

    def get_puzzle(self):
        return self._puzzle

    def get_moves(self):
        if self._puzzle is None:
            return 0
        return self._puzzle.get_moves()

    def get_incorrect_count(self):
        if self._puzzle is None:
            return 0
        return self._puzzle.get_incorrect_count()

    def _blank_image_for_current_grid(self):
        return self._processor.prepare_image(self._make_blank_board(self._grid_size), self._grid_size)

    def reset_puzzle(self):
        if self._image is None:
            self._image = self._blank_image_for_current_grid()
            self._puzzle = Puzzle(self._image.copy(), self._grid_size)
        else:
            self._puzzle = Puzzle(self._image.copy(), self._grid_size)
        self._selected_tile = None
        self._hint_positions = []
        self._hint_count = 0
        self._hint_limit_reached = False
        self._update_selection_label()
        self._refresh_hint_button()
        if self._status_var is not None:
            self._status_var.set("Puzzle reset.")
        self.refresh_display()

    def scramble_round(self):
        try:
            if self._puzzle is None:
                self.reset_puzzle()
            self._puzzle.scramble()
            self._selected_tile = None
            self._hint_positions = []
            self._hint_count = 0
            self._hint_limit_reached = False
            self._refresh_hint_button()
            if self._status_var is not None:
                self._status_var.set("New round started.")
        except Exception as exc:  # pragma: no cover - GUI interaction path
            self.show_error(str(exc))
        finally:
            self.refresh_display()

    def load_image(self, file_path=None):
        if file_path is None and self._root is not None:
            file_path = filedialog.askopenfilename(
                title="Select an image",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
            )

        if not file_path:
            return False

        try:
            image = self._processor.load_image(file_path)
            self._image = self._processor.prepare_image(image, self._grid_size)
            self._puzzle = Puzzle(self._image.copy(), self._grid_size)
            self._puzzle.scramble()
            self._selected_tile = None
            self._hint_positions = []
            self._hint_count = 0
            self._hint_limit_reached = False
            self._refresh_hint_button()
            if self._status_var is not None:
                self._status_var.set(f"Loaded {os.path.basename(file_path)}.")
            self.refresh_display()
            return True
        except (ValueError, FileNotFoundError) as exc:
            self.show_error(str(exc))
            return False

    def show_hint(self):
        if self._puzzle is None:
            return False
        if self._hint_limit_reached:
            if self._status_var is not None:
                self._status_var.set("Hint limit reached for this image.")
            return False

        incorrect_indexes = [
            index for index in range(self._puzzle.get_grid_size() ** 2)
            if not self._puzzle.is_tile_correct(index)
        ]
        if not incorrect_indexes:
            if self._status_var is not None:
                self._status_var.set("The puzzle is already solved.")
            return False

        index = incorrect_indexes[0]
        self._hint_positions = [index, self._puzzle.get_tile_id(index)]
        self._hint_count += 1
        if self._hint_count >= 3:
            self._hint_limit_reached = True
        self._refresh_hint_button()
        if self._status_var is not None:
            self._status_var.set(f"Hint: tile {index} belongs at position {self._puzzle.get_tile_id(index)}.")
        self.refresh_display()
        return True

    def _tile_index_from_event(self, event):
        if self._playable_canvas is None:
            return None

        board_x = event.x
        board_y = event.y
        board_size = self._get_canvas_board_size(self._playable_canvas)
        tile_size = board_size / self._grid_size

        if board_x < 0 or board_y < 0:
            return None
        if board_x >= board_size or board_y >= board_size:
            return None

        row = int(board_y // tile_size)
        column = int(board_x // tile_size)
        if row < 0 or column < 0:
            return None
        if row >= self._grid_size or column >= self._grid_size:
            return None

        index = row * self._grid_size + column
        if 0 <= index < self._grid_size ** 2:
            return index
        return None

    def _get_canvas_board_size(self, canvas):
        if canvas is None:
            return 420
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        return min(width, height)

    def _on_reference_click(self, event):
        if self._puzzle is None:
            return
        self._selected_tile = None
        self._update_selection_label()
        self.refresh_display()

    def _on_tile_click(self, event):
        index = self._tile_index_from_event(event)
        if index is None:
            return
        self._select_or_swap_tile(index)

    def _on_tile_rotate(self, event):
        index = self._tile_index_from_event(event)
        if index is None:
            return
        if self._puzzle is None or self._puzzle.is_input_locked():
            return
        success = self._puzzle.rotate_tile(index, 90)
        if success:
            self._selected_tile = None
            self._hint_positions = []
            self._update_selection_label()
            self.refresh_display()
            if self._status_var is not None:
                self._status_var.set(f"Rotated tile {index}.")

    def _on_tile_flip(self, event):
        index = self._tile_index_from_event(event)
        if index is None:
            return
        if self._puzzle is None or self._puzzle.is_input_locked():
            return
        success = self._puzzle.flip_tile(index, "horizontal")
        if success:
            self._selected_tile = None
            self._hint_positions = []
            self._update_selection_label()
            self.refresh_display()
            if self._status_var is not None:
                self._status_var.set(f"Flipped tile {index}.")

    def _select_or_swap_tile(self, index):
        if self._puzzle is None or self._puzzle.is_input_locked():
            return
        if self._selected_tile is None:
            self._selected_tile = index
            self._update_selection_label()
            if self._status_var is not None:
                self._status_var.set(f"Selected tile {index}.")
            self.refresh_display()
            return

        if self._selected_tile == index:
            self._selected_tile = None
            self._update_selection_label()
            if self._status_var is not None:
                self._status_var.set("Selection cleared.")
            self.refresh_display()
            return

        old_selection = self._selected_tile
        success = self._puzzle.swap_tiles(old_selection, index)
        self._selected_tile = None
        self._hint_positions = []
        self._update_selection_label()
        if success and self._status_var is not None:
            self._status_var.set(f"Swapped tiles {old_selection} and {index}.")
        self.refresh_display()

    def _update_selection_label(self):
        if self._selected_tile_var is None:
            return
        if self._selected_tile is None:
            self._selected_tile_var.set("None")
        else:
            self._selected_tile_var.set(str(self._selected_tile))

    def refresh_display(self):
        self._update_selection_label()
        if self._moves_var is not None:
            self._moves_var.set(str(self.get_moves()))
        if self._incorrect_var is not None:
            self._incorrect_var.set(str(self.get_incorrect_count()))

        if self._puzzle is None:
            return

        if self._reference_canvas is not None:
            self._draw_reference_canvas()
        if self._playable_canvas is not None:
            self._draw_playable_canvas()

    def _draw_reference_canvas(self):
        self._reference_canvas.delete("all")
        board_size = self._get_canvas_board_size(self._reference_canvas)
        image = self._puzzle.get_original_image()
        photo = self._photo_for_array(image, board_size, board_size)
        self._reference_photo = photo
        self._reference_canvas.create_image(0, 0, anchor="nw", image=photo)
        self._draw_grid(self._reference_canvas, self._puzzle.get_grid_size(), board_size, board_size)

        if self._hint_positions and len(self._hint_positions) >= 2:
            home_index = self._hint_positions[1]
            if isinstance(home_index, int):
                self._draw_hint_marker(self._reference_canvas, home_index, self._puzzle.get_grid_size(), board_size, "#1a73e8")

    def _draw_playable_canvas(self):
        self._playable_canvas.delete("all")
        board_size = self._get_canvas_board_size(self._playable_canvas)
        image = self._puzzle.get_current_image()
        photo = self._photo_for_array(image, board_size, board_size)
        self._playable_photo = photo
        self._playable_canvas.create_image(0, 0, anchor="nw", image=photo)
        self._draw_grid(self._playable_canvas, self._puzzle.get_grid_size(), board_size, board_size)

        if self._selected_tile is not None:
            self._draw_selection_outline(self._playable_canvas, self._selected_tile, self._puzzle.get_grid_size(), board_size)

        for index in self._hint_positions:
            if isinstance(index, int):
                self._draw_hint_marker(self._playable_canvas, index, self._puzzle.get_grid_size(), board_size, "#1a73e8")

        for index in range(self._puzzle.get_grid_size() ** 2):
            if self._puzzle.is_tile_correct(index):
                self._draw_correct_marker(self._playable_canvas, index, self._puzzle.get_grid_size(), board_size)

    def _draw_grid(self, canvas, grid_size, width, height):
        tile_size = min(width, height) / grid_size
        for line in range(1, grid_size):
            x = line * tile_size
            canvas.create_line(x, 0, x, height, fill="#9bb0be", width=1)
            y = line * tile_size
            canvas.create_line(0, y, width, y, fill="#9bb0be", width=1)

    def _draw_selection_outline(self, canvas, tile_index, grid_size, board_size):
        tile_size = board_size / grid_size
        row, column = divmod(tile_index, grid_size)
        x1 = column * tile_size + 3
        y1 = row * tile_size + 3
        x2 = (column + 1) * tile_size - 3
        y2 = (row + 1) * tile_size - 3
        canvas.create_rectangle(x1, y1, x2, y2, outline="#0a7d3a", width=3)

    def _draw_hint_marker(self, canvas, tile_index, grid_size, board_size, colour):
        tile_size = board_size / grid_size
        row, column = divmod(tile_index, grid_size)
        x = column * tile_size + tile_size / 2
        y = row * tile_size + tile_size / 2
        canvas.create_oval(x - 12, y - 12, x + 12, y + 12, outline=colour, width=3)

    def _draw_correct_marker(self, canvas, tile_index, grid_size, board_size):
        tile_size = board_size / grid_size
        row, column = divmod(tile_index, grid_size)
        x = column * tile_size + tile_size * 0.66
        y = row * tile_size + tile_size * 0.35
        canvas.create_text(x, y, text="✓", fill="#13a652", font=("Helvetica", 16, "bold"))

    def _photo_for_array(self, image, width, height):
        if Image is None or ImageTk is None:
            return None
        rgb_image = self._processor.to_rgb(image)
        pillow_image = Image.fromarray(rgb_image)
        if width and height:
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            pillow_image = pillow_image.resize((width, height), resampling)
        return ImageTk.PhotoImage(pillow_image)

    def show_error(self, message):
        if self._root is not None:
            messagebox.showerror("Puzzle error", message)
        else:
            print(f"Puzzle error: {message}")

    def run(self):
        if self._root is not None:
            self._root.mainloop()


def main():
    app = PuzzleGUI()
    app.run()


if __name__ == "__main__":
    main()

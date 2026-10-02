# HIT137 Assignment 3: Image Puzzle Game

A Tkinter desktop game. You load a picture, it gets cut into a grid of tiles and scrambled with swaps, rotations and flips, and you have to put it back together.

Repository: https://github.com/shreeyaniraula/HIT137

## Team

| Task | Member | Work |
| --- | --- | --- |
| 1 | Mohd Ratib | Image loading, resizing, padding, splitting and reassembly (`image_processor.py`) |
| 2 | Shreeya | Tile, transformations and puzzle model (`tile.py`, `transformations.py`, `puzzle.py`) |
| 3 | Vibhi Singh | Tkinter interface and mouse interaction (`gui.py`) |
| 4 | Udit Vachhani | Hints, Solve, completion, timer, difficulty, decoys, integration tests and docs (`round_features.py`, `gui.py`) |

## Setup and running

You need Python 3 (we tested with 3.12). Tkinter comes with the normal Python installer on Windows and macOS. On Ubuntu, install `python3-tk`.

Run these from the project folder, not from inside `src`.

Windows:

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m src.main
```

macOS / Linux:

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m src.main
```

Sample pictures are in `assets/` (PNG, JPG and BMP).

## How to play

1. Pick a grid size (3x3, 4x4 or 5x5) and a difficulty, then click **Load image**.
2. The original picture is on the left for reference. The scrambled one is on the right.
3. Fix the tiles using the mouse:

| Action | Input |
| --- | --- |
| Select / deselect a tile | Left click |
| Swap two tiles | Left click one tile, then another |
| Rotate 90 degrees clockwise | Right click |
| Flip horizontally | Shift + left click |

A green tick appears on a tile once it is in the right place and the right way round. The game tells you when the whole picture is restored and then locks the board.

Buttons and options:

- **Hint** circles one wrong tile in blue and circles where it belongs on the original. The circles disappear after your next move. You get 3 hints per image.
- **Solve** puts every tile back and resets moves and tiles left to 0.
- **New round** scrambles the same picture again.
- **Difficulty** changes how many transformations are applied (see the table below).
- **Time limit** adds a countdown. When it hits zero the board locks, but you can still press Solve or start again.
- **Decoys** adds a tray of fake pieces cut from the picture. You can swap them onto the board, but the puzzle only counts as finished once all real tiles are back.

## Features against the marking rubric

### OOP design

| Class | File | Notes |
| --- | --- | --- |
| `ImageProcessor` | `image_processor.py` | Loads, resizes, pads, splits and joins images |
| `Tile`, `DecoyTile` | `tile.py` | Tile keeps its id, pixels and orientation. `DecoyTile` inherits from `Tile` and overrides `is_correct()` |
| `Transformation`, `Swap`, `Rotate`, `Flip` | `transformations.py` | Abstract base class with an `apply()` method that each subclass implements |
| `Puzzle` | `puzzle.py` | Board order, moves, scrambling, solved check and input lock |
| `HintManager`, `Difficulty`, `CountdownTimer`, `DecoyFactory` | `round_features.py` | Round features used by the GUI |
| `PuzzleGUI` | `gui.py` | Window, drawing and mouse events |

- **Encapsulation:** all state is in private attributes (`_tiles`, `_moves`, and so on) and is only reached through methods. Images are returned as copies.
- **Inheritance:** `Swap`, `Rotate` and `Flip` inherit from `Transformation`, and `DecoyTile` inherits from `Tile`.
- **Polymorphism:** the scramble calls `operation.apply(tiles)` without knowing which operation it is. `Puzzle` calls `tile.is_correct()` on normal and decoy tiles the same way.
- **Class interaction:** `PuzzleGUI` uses `Puzzle`, which uses `ImageProcessor`, `Tile` and the transformation classes.
- **Error handling:** cancelling the file dialog does nothing. Non-image files, unsupported extensions and missing files show an error message box. Clicks outside the image are ignored.

### Image processing

- JPG, JPEG, PNG and BMP are loaded with OpenCV.
- The image is resized to fit a 420 px board without changing the aspect ratio, then padded so the grid divides evenly.
- Tiles are split out and joined back into one image for display after every move.
- Each load randomly picks the target tiles, the rotation angles (90, 180 or 270) and the flip directions (horizontal or vertical). All transformations are generated at once, and no tile is targeted twice.
- The number of transformations grows with the grid size:

| Difficulty | 3x3 | 4x4 | 5x5 | Time limit |
| --- | --- | --- | --- | --- |
| Easy | 5 | 10 | 16 | 20 s per tile |
| Normal | 6 | 12 | 20 | 12 s per tile |
| Hard | 7 | 13 | 21 | 8 s per tile |

Normal uses the 6 / 12 / 20 counts from the brief.

### Tkinter GUI and gameplay

- Original and puzzle images are shown side by side, with a faint grid over the puzzle.
- The grid size is chosen before loading. Loading a new image resets moves, hints, selection and the timer.
- The selected tile gets an orange border, and the image is redrawn after every action.
- Moves and tiles left are shown and updated after every action.
- Hints, Solve and the completion message work as described above.

### Extra features

- Decoy tiles (dummy puzzle items)
- Time limit
- Difficulty levels

## Project structure

```
src/
  main.py              start the app
  gui.py               Tkinter window
  image_processor.py   OpenCV image handling
  tile.py              Tile and DecoyTile
  transformations.py   Swap, Rotate, Flip
  puzzle.py            puzzle model
  round_features.py    hints, difficulty, timer, decoys
tests/                 unit and integration tests
assets/                sample images
outputs/               screenshots
```

## Testing

```
.venv\Scripts\python -m unittest discover -s tests -v      (Windows)
.venv/bin/python -m unittest discover -s tests -v          (macOS / Linux)
```

There are 91 tests. The 4 tests that open a real window are skipped if there is no display. The tests cover:

- Loading every format and image shape at all three grid sizes
- Invalid files and a cancelled dialog
- Scramble counts and no tile being targeted twice
- Click-to-tile mapping, including tile edges
- Swap, rotate and flip, and the move counts
- Hint limit and hints clearing after a move
- Solve after random moves
- Finishing every grid size using only normal moves, then checking the lock
- Resetting when a new image is loaded
- Timer expiry
- Decoys
- Real mouse events in a Tk window

## Screenshots

| File | Shows |
| --- | --- |
| `outputs/01_start_screen.png` | Start screen |
| `outputs/02_loaded_3x3_scrambled.png` | Image loaded and scrambled |
| `outputs/03_hint_markers.png` | Hint circles on both images |
| `outputs/04_progress_ticks_and_selection.png` | Green ticks and a selected tile |
| `outputs/05_completion_message.png` | Completion message |
| `outputs/06_4x4_hard.png` | 4x4 on Hard |
| `outputs/07_5x5_timer_and_decoy_tray.png` | 5x5 with timer and decoy tray |
| `outputs/08_solve_button.png` | After pressing Solve |
| `outputs/09_time_up_locked.png` | Time's up |
| `outputs/10_invalid_file_error.png` | Error for an invalid file |

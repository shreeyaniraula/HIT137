# HIT137 Group Assignment 3: Image Puzzle Game

## Project overview

This repository is being prepared for HIT137 Group Assignment 3, a Python desktop image-restoration puzzle worth 30% of the unit mark. The planned application lets a player load an image, split it into tiles, and restore the original picture after the tiles have been scrambled using swaps, rotations and flips. The project is under development; the application has not been implemented yet.

The required technologies are:

| Technology | Planned use |
| --- | --- |
| Python | Application logic |
| Tkinter | Desktop interface and interaction |
| OpenCV | Image loading and processing |
| NumPy | Image and tile arrays |
| Pillow | Displaying processed images in Tkinter |

No database or API keys are required.

## Team and task allocation

| Task | Member | Responsibility |
| --- | --- | --- |
| Task 1 | Mohd Ratib | Image loading and processing |
| Task 2 | Shreeya | Puzzle model and transformations |
| Task 3 |  | Tkinter interface and interaction |
| Task 4 |  | Round features, challenges and integration testing |

### Task 1: Mohd Ratib

- Load JPG, PNG and BMP images using OpenCV.
- Validate files and report loading failures to the GUI.
- Resize images while preserving aspect ratio.
- Pad or crop images so they can be divided into equal square tiles.
- Support 3 × 3, 4 × 4 and 5 × 5 grids.
- Split images into independent tile arrays and reassemble tiles into one image.
- Convert BGR image data to RGB for display.
- Verify supported formats and image dimensions.

### Task 2: Shreeya

- Implement `Tile` and `Puzzle` classes.
- Track each tile's original identity, current position and orientation.
- Implement a shared `Transformation` class with `Swap`, `Rotate` and `Flip` subclasses.
- Demonstrate purposeful inheritance and polymorphism through a common `apply` method.
- Generate random initial scrambles using all three transformation types.
- Ensure no tile is targeted twice during initial scrambling, including both participants in a swap.
- Implement player swaps, rotations and flips.
- Maintain the authoritative move count and tile-correctness calculation.
- Expose the model methods needed by Tasks 3 and 4.

### Task 3: Tkinter interface and interaction

- Build the Tkinter application and organise widgets into clear methods.
- Provide the file chooser and grid selector.
- Display the original on the left and playable image on the right.
- Implement mouse bindings and accurate click-to-tile mapping.
- Draw grid lines, selection borders, green ticks and blue hint circles.
- Display counters and controls, and present error and completion messages.
- Implement moving-board presentation and correct coordinate handling.
- Integrate model and round-feature behaviour without duplicating game state.

### Task 4: Round features, challenges and integration testing

- Implement hint selection and the three-hint allowance.
- Coordinate Solve and completion behaviour with the puzzle model.
- Implement timer, difficulty settings and dummy-item challenge logic.
- Coordinate challenge controls and presentation with Task 3.
- Check round resets, input locking and edge cases.
- Maintain integration test scenarios, usage documentation and output screenshots.
- Prepare the submission checklist.

All members must test and document their own work, commit their own contributions, and participate in integration. Task 4 is not solely responsible for testing everyone else's code.

## Required functionality checklist

- [ ] Default 3 × 3 grid, with 4 × 4 and 5 × 5 selectable before loading.
- [ ] JPG, PNG and BMP support.
- [ ] Aspect-ratio-preserving resize and even tile division.
- [ ] Side-by-side reference and playable images.
- [ ] Reference image accepts no gameplay input.
- [ ] Faint puzzle grid.
- [ ] Random swaps, 90°/180°/270° rotations, and horizontal/vertical flips during scrambling.
- [ ] All initial transformations generated before gameplay.
- [ ] Scramble count increases with grid size.
- [ ] No tile targeted twice during initial scrambling.
- [ ] Reassemble transformed tiles into one display image.
- [ ] Left click selects a tile and highlights it.
- [ ] Clicking another tile swaps the pair and clears selection.
- [ ] Clicking the selected tile deselects it.
- [ ] Right click rotates a tile 90° clockwise.
- [ ] Shift + left click flips horizontally without also triggering a normal left-click action.
- [ ] Green ticks require both correct position and orientation.
- [ ] Each swap, rotation or flip counts as one move.
- [ ] Selection, deselection and ignored clicks do not count as moves.
- [ ] Display moves and incorrect-tile count, updated after each move.
- [ ] Hint marks an incorrect tile on the puzzle and its home position on the reference using blue circles.
- [ ] Hint markers disappear after the next actual move.
- [ ] Maximum three hints per image, followed by a disabled Hint button.
- [ ] Solve restores all positions and orientations and resets moves and incorrect tiles to zero.
- [ ] Completion notification and locked gameplay input.
- [ ] Loading a new image fully resets the round.
- [ ] Cancelled dialogs and off-image clicks are handled safely.
- [ ] Invalid or unreadable files produce message-box errors.
- [ ] All three grid sizes are fully playable.
- [ ] Constructors, methods, class interaction, encapsulation, inheritance and polymorphism are used meaningfully.
- [ ] Consistent coding style and documentation.

## Planned scrambling approach

The assignment brief gives 6, 12 and 20 transformations as examples. The team plans to adopt these counts for its standard preset. A swap is one operation but targets two tiles, so the number of distinct targeted tiles is the number of rotations and flips plus twice the number of swaps.

| Grid | Swaps | Rotations | Flips | Operations | Distinct tiles targeted |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 × 3 | 2 | 2 | 2 | 6 | 8 |
| 4 × 4 | 3 | 5 | 4 | 12 | 15 |
| 5 × 5 | 4 | 8 | 8 | 20 | 24 |

Targets, rotation angles and flip directions will be randomised. The unique-target restriction applies to initial scrambling only; later player moves may target tiles again.

## Planned enhancements

The following rubric suggestions are planned features, not implemented functionality:

- [ ] Dummy puzzle items.
- [ ] Time limits.
- [ ] Difficulty levels.
- [ ] Moving puzzles.

The team's proposed interpretations are:

- **Dummy items:** A separate decoy tray that does not remove required picture tiles.
- **Time limits:** An optional countdown mode that locks gameplay at expiry but permits Solve or loading another image.
- **Difficulty:** Presets that adjust valid scramble counts and challenge settings while retaining all grid choices.
- **Moving puzzles:** Optional bounded movement of the playable board, with overlays and click coordinates kept aligned.

The rubric does not precisely define dummy items or moving puzzles. These are team interpretations that may be refined following lecturer clarification. Completing these extras does not guarantee a D or HD grade.

## Planned structure and integration rules

These files are planned and have not been created yet:

| Planned file | Intended role |
| --- | --- |
| `src/main.py` | Application entry point and startup wiring |
| `src/image_processor.py` | Image validation, preparation, tiling and reassembly |
| `src/tile.py` | Tile identity, position and orientation state |
| `src/transformations.py` | Shared transformation interface and swap, rotate and flip operations |
| `src/puzzle.py` | Puzzle state, scrambling, player moves, move counts and correctness |
| `src/gui.py` | Tkinter widgets, image display, input and visual overlays |
| `src/round_features.py` | Hints, solve coordination, timer, difficulty and challenge behaviour |
| `requirements.txt` | Python package dependencies for the application |

The `assets/` folder is for image assets needed by the project. The `tests/` folder is for automated and integration tests. The `outputs/` folder is for required output screenshots and other submission evidence.

Shared integration rules:

- Internal images use NumPy arrays in BGR colour order; convert to RGB at the display boundary.
- Tiles use row-major ordering, starting at the top-left.
- Keep an untouched prepared original image.
- Track tile identity and combined rotation/reflection state.
- The puzzle model owns game state and move counts; the GUI owns widgets and visual overlays.
- Draw overlays on display copies, not on underlying tile data.
- Keep a single source of truth for round status and hint usage.
- Agree on shared method names before implementing dependent modules.
- Use Tkinter scheduling for timers and animation.
- Cancel old callbacks on round changes and window closure.

## Development setup

Application setup instructions will be completed when implementation begins. Planned dependencies are Python, OpenCV, NumPy and Pillow. Tkinter is supplied with many Python installations and is not installed using pip. No application run or installation command is available yet because the application files and `requirements.txt` have not been created.

## Git workflow

The assignment requires a public GitHub repository, and all group members must be added as collaborators. Each member should work on a task branch. Suggested branch names are:

- `task-1-image-processing`
- `task-2-puzzle-logic`
- `task-3-gui`
- `task-4-round-features`

Use focused commits with meaningful messages, push contributions regularly, and merge through pull requests. Check the combined application after integration. Avoid committing virtual environments, caches, secrets or local editor files. Do not fabricate contributions or commit history. This document describes the branch workflow only; no task branches are created or selected here.

## Testing plan

- [ ] Test every supported image format across all grid sizes.
- [ ] Test portrait, landscape and square images.
- [ ] Test invalid files and cancelled dialogs.
- [ ] Test unique scramble targets and expected operation counts.
- [ ] Test all mouse controls and tile boundaries.
- [ ] Test combined rotations and flips.
- [ ] Test move counts and green ticks.
- [ ] Test hint positions, expiry and allowance.
- [ ] Test Solve after arbitrary player moves.
- [ ] Test completion locking.
- [ ] Test full reset on a new image.
- [ ] Test timer expiry and cancelled callbacks.
- [ ] Test decoys and moving-board click accuracy.
- [ ] Check Mac and Windows interactions where available.

## Submission checklist

- [ ] Public repository and group collaborator access verified.
- [ ] Contributions recorded throughout development.
- [ ] Correct repository URL in `github_link.txt`.
- [ ] All programming files, necessary assets and outputs included.
- [ ] Output screenshots demonstrate the required features.
- [ ] ZIP opens and runs using the documented setup.
- [ ] ZIP uploaded to Learline.
- [ ] Deadline checked on Learline.

The supplied brief does not specify a deadline or a numerical points formula beyond moves and incorrect tiles. Check Learline for the deadline. The brief states a late penalty of 5% of the total available marks per day.
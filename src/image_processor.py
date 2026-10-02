"""Image loading, resizing, tiling and reassembly using OpenCV."""

import os

import cv2
import numpy as np


class ImageProcessor:
    """Load images and prepare them for the puzzle board."""

    def __init__(self, max_size=420):
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 5:
            raise ValueError("max_size must be an integer of at least 5 pixels.")

        self._supported_formats = [".jpg", ".jpeg", ".png", ".bmp"]
        self._max_size = max_size

    def _check_grid_size(self, grid_size):
        if isinstance(grid_size, bool) or not isinstance(grid_size, int):
            raise ValueError("grid_size must be an integer value of 3, 4 or 5.")
        if grid_size not in (3, 4, 5):
            raise ValueError("grid_size must be 3, 4 or 5.")

    def _check_image(self, image, name="image"):
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError(f"{name} must be a non-empty NumPy array.")
        if image.size == 0:
            raise ValueError(f"{name} must not be empty.")
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"{name} must be a three-channel array.")
        if image.dtype != np.uint8:
            raise ValueError(f"{name} must have dtype uint8.")

    def load_image(self, file_path):
        """Load an image file and return it as a BGR array."""
        if file_path is None or file_path.strip() == "":
            raise ValueError("No file path was provided.")

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        _, file_extension = os.path.splitext(file_path)
        if file_extension.lower() not in self._supported_formats:
            raise ValueError(
                "Unsupported image format. Please use JPG, JPEG, PNG, or BMP files."
            )

        try:
            image = cv2.imread(file_path, cv2.IMREAD_COLOR)
        except cv2.error as error:
            raise ValueError(f"Could not read image file: {file_path}") from error

        if image is None:
            raise ValueError(f"The file is not a readable image: {file_path}")

        return image

    def prepare_image(self, image, grid_size=3):
        """Resize the image to fit the board and pad it to a square."""
        self._check_grid_size(grid_size)
        self._check_image(image)

        height, width = image.shape[:2]
        board_size = (self._max_size // grid_size) * grid_size
        scale_factor = board_size / max(height, width)

        # keep the aspect ratio
        new_width = max(1, min(board_size, int(round(width * scale_factor))))
        new_height = max(1, min(board_size, int(round(height * scale_factor))))

        interpolation = cv2.INTER_AREA if scale_factor < 1 else cv2.INTER_LINEAR
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=interpolation)

        # pad evenly so the picture stays in the middle
        vertical_padding = board_size - new_height
        horizontal_padding = board_size - new_width
        top = vertical_padding // 2
        left = horizontal_padding // 2

        return cv2.copyMakeBorder(
            resized_image,
            top,
            vertical_padding - top,
            left,
            horizontal_padding - left,
            cv2.BORDER_CONSTANT,
            value=(240, 240, 240),
        )

    def split_image(self, image, grid_size=3):
        """Split a square image into tiles, left to right then top to bottom."""
        self._check_grid_size(grid_size)
        self._check_image(image)

        height, width = image.shape[:2]
        if height != width:
            raise ValueError("image must be square before splitting.")
        if height % grid_size != 0:
            raise ValueError("image dimensions must divide evenly by grid_size.")

        tile_size = height // grid_size
        tiles = []
        for row in range(grid_size):
            for column in range(grid_size):
                y = row * tile_size
                x = column * tile_size
                tiles.append(image[y:y + tile_size, x:x + tile_size].copy())

        return tiles

    def reassemble_image(self, tiles, grid_size=3):
        """Join a list of tiles back into one square image."""
        self._check_grid_size(grid_size)

        if not isinstance(tiles, (list, tuple)):
            raise ValueError("tiles must be a list or tuple of tile arrays.")

        expected_count = grid_size * grid_size
        if len(tiles) != expected_count:
            raise ValueError(
                f"tiles must contain exactly {expected_count} entries for a {grid_size}x{grid_size} grid."
            )

        for tile in tiles:
            self._check_image(tile, "Each tile")

        tile_size = tiles[0].shape[0]
        if tiles[0].shape[1] != tile_size:
            raise ValueError("Each tile must be square.")
        for tile in tiles[1:]:
            if tile.shape[:2] != (tile_size, tile_size):
                raise ValueError("All tiles must have the same dimensions.")

        board_size = tile_size * grid_size
        completed_image = np.zeros((board_size, board_size, 3), dtype=np.uint8)
        for index, tile in enumerate(tiles):
            row, column = divmod(index, grid_size)
            y = row * tile_size
            x = column * tile_size
            completed_image[y:y + tile_size, x:x + tile_size] = tile

        return completed_image

    def to_rgb(self, image):
        """Convert a BGR image to RGB for showing in Tkinter."""
        self._check_image(image)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

"""Load and validate image files for the puzzle application."""

import os

import cv2
import numpy as np


class ImageProcessor:
    """Load and prepare images for the puzzle game.

    The GUI should handle file-dialog cancellation before calling this method.
    """

    def __init__(self, max_size=420):
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 5:
            raise ValueError("max_size must be an integer of at least 5 pixels.")

        self._supported_formats = [".jpg", ".jpeg", ".png", ".bmp"]
        self._max_size = max_size

    def load_image(self, file_path):
        """Return an image as a BGR NumPy array after validating the file.

        The GUI should handle file-dialog cancellation before calling this method.
        """
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
        """Resize and pad an image so it fits a square board for a puzzle grid."""
        if isinstance(grid_size, bool) or not isinstance(grid_size, int):
            raise ValueError("grid_size must be an integer value of 3, 4 or 5.")

        if grid_size not in (3, 4, 5):
            raise ValueError("grid_size must be 3, 4 or 5.")

        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("image must be a non-empty NumPy array.")

        if image.size == 0:
            raise ValueError("image must not be empty.")

        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image must be a three-channel array.")

        if image.dtype != np.uint8:
            raise ValueError("image must have dtype uint8.")

        height, width = image.shape[:2]
        if height <= 0 or width <= 0:
            raise ValueError("image dimensions must be greater than zero.")

        board_size = (self._max_size // grid_size) * grid_size

        long_side = max(height, width)
        scale_factor = board_size / long_side

        # Keep the original aspect ratio while ensuring the resized dimensions stay within the board.
        new_width = max(1, min(board_size, int(round(width * scale_factor))))
        new_height = max(1, min(board_size, int(round(height * scale_factor))))

        interpolation = cv2.INTER_AREA if scale_factor < 1 else cv2.INTER_LINEAR
        resized_image = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=interpolation,
        )

        # Add balanced padding so the image stays centred in the square board.
        vertical_padding = board_size - new_height
        horizontal_padding = board_size - new_width
        top = vertical_padding // 2
        bottom = vertical_padding - top
        left = horizontal_padding // 2
        right = horizontal_padding - left

        padded_image = cv2.copyMakeBorder(
            resized_image,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=(240, 240, 240),
        )

        return padded_image

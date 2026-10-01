"""Load and validate image files for the puzzle application."""

import os

import cv2


class ImageProcessor:
    """Load and validate image files for the puzzle application.

    The GUI should handle file-dialog cancellation before calling this method.
    """

    def __init__(self):
        self._supported_formats = [".jpg", ".jpeg", ".png", ".bmp"]

    def load_image(self, file_path):
        """Return an image as a BGR NumPy array after validating the file.

        The GUI should handle file-dialog cancellation before calling this method.
        """
        if file_path is None or file_path.strip() == "":
            raise ValueError("No file path was provided.")

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        file_name, file_extension = os.path.splitext(file_path)
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

"""Application entry point for the image puzzle game."""

from src.gui import PuzzleGUI


def main():
    app = PuzzleGUI()
    app.run()


if __name__ == "__main__":
    main()

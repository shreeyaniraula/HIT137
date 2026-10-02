"""Application entry point for the image puzzle game."""

import tkinter as tk

from src.gui import PuzzleGUI


def main():
    root = tk.Tk()
    app = PuzzleGUI(root)
    app.run()


if __name__ == "__main__":
    main()

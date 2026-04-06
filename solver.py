"""
Main menu launcher for the Puzzle Solver repository.
Use this as the entry point as more puzzle types are added.
"""

import tkinter as tk
from tkinter import ttk


class PuzzleSolverHome:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Puzzle Solver Hub")
        self.root.geometry("700x450")
        self.root.configure(bg="#eef2f7")

        self.sudoku_window = None
        self.setup_ui()

    def setup_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            container,
            text="Puzzle Solver Hub",
            font=("Helvetica", 24, "bold")
        )
        title.pack(pady=(10, 8))

        subtitle = ttk.Label(
            container,
            text="Launch puzzle modules from one place",
            font=("Helvetica", 11)
        )
        subtitle.pack(pady=(0, 20))

        ttk.Separator(container, orient="horizontal").pack(fill="x", pady=8)

        sudoku_card = ttk.LabelFrame(container, text="Available Now", padding=14)
        sudoku_card.pack(fill="x", pady=14)

        self.sudoku_btn = ttk.Button(
            sudoku_card,
            text="Sudoku Solver",
            command=self.launch_sudoku,
            width=30
        )
        self.sudoku_btn.pack(pady=(4, 8))

        ttk.Label(
            sudoku_card,
            text="Supports 1x1, 4x4, 9x9, and 16x16 boards with keyboard input.",
            font=("Helvetica", 10)
        ).pack()

        future_card = ttk.LabelFrame(container, text="Coming Next", padding=14)
        future_card.pack(fill="x", pady=(0, 10))
        ttk.Label(
            future_card,
            text="Add future puzzle launch buttons here (N-Queens, Crosswords, etc.).",
            font=("Helvetica", 10)
        ).pack()

        self.status_label = ttk.Label(
            container,
            text="Ready.",
            font=("Helvetica", 10)
        )
        self.status_label.pack(pady=(10, 0), anchor="w")

    def launch_sudoku(self):
        try:
            if self.sudoku_window is not None and self.sudoku_window.winfo_exists():
                self.sudoku_window.focus_force()
                self.status_label.config(text="Sudoku window is already open.")
                return

            from sudoku_solver.ui import SudokuSolverUI

            self.sudoku_window = tk.Toplevel(self.root)
            self.sudoku_window.protocol("WM_DELETE_WINDOW", self._on_sudoku_close)
            SudokuSolverUI(self.sudoku_window)
            self.sudoku_btn.config(state="disabled")
            self.status_label.config(text="Sudoku solver launched.")
        except Exception as exc:
            self.status_label.config(text=f"Error launching Sudoku: {exc}")

    def _on_sudoku_close(self):
        if self.sudoku_window is not None and self.sudoku_window.winfo_exists():
            self.sudoku_window.destroy()
        self.sudoku_window = None
        self.sudoku_btn.config(state="normal")
        self.status_label.config(text="Sudoku window closed.")


def main():
    root = tk.Tk()
    PuzzleSolverHome(root)
    root.mainloop()


if __name__ == "__main__":
    main()

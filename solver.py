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
        self.queens_window = None
        self.tango_window = None
        self.zip_window = None
        self.setup_ui()

    def _hide_home(self):
        self.root.withdraw()

    def _show_home(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

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

        self.queens_btn = ttk.Button(
            sudoku_card,
            text="Queens",
            command=self.launch_queens,
            width=30
        )
        self.queens_btn.pack(pady=(12, 8))

        ttk.Label(
            sudoku_card,
            text="Solves one-queen-per-row/column/region puzzles with no-touch constraints.",
            font=("Helvetica", 10)
        ).pack()

        self.tango_btn = ttk.Button(
            sudoku_card,
            text="Tango",
            command=self.launch_tango,
            width=30
        )
        self.tango_btn.pack(pady=(12, 8))

        ttk.Label(
            sudoku_card,
            text="Binary puzzle: avoid 3-in-a-row and keep equal symbol counts per row/column.",
            font=("Helvetica", 10)
        ).pack()

        self.zip_btn = ttk.Button(
            sudoku_card,
            text="Zip",
            command=self.launch_zip,
            width=30
        )
        self.zip_btn.pack(pady=(12, 8))

        ttk.Label(
            sudoku_card,
            text="Connect matching numbers with paths that cover every cell.",
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
                self._hide_home()
                return

            from sudoku_solver.ui import SudokuSolverUI

            self.sudoku_window = tk.Toplevel(self.root)
            self.sudoku_window.protocol("WM_DELETE_WINDOW", self._on_sudoku_close)
            SudokuSolverUI(self.sudoku_window)
            self.sudoku_btn.config(state="disabled")
            self.status_label.config(text="Sudoku solver launched.")
            self._hide_home()
        except Exception as exc:
            self._show_home()
            self.status_label.config(text=f"Error launching Sudoku: {exc}")

    def _on_sudoku_close(self):
        if self.sudoku_window is not None and self.sudoku_window.winfo_exists():
            self.sudoku_window.destroy()
        self.sudoku_window = None
        self.sudoku_btn.config(state="normal")
        self.status_label.config(text="Sudoku window closed.")
        self._show_home()

    def launch_queens(self):
        try:
            if self.queens_window is not None and self.queens_window.winfo_exists():
                self.queens_window.focus_force()
                self.status_label.config(text="Queens window is already open.")
                self._hide_home()
                return

            from linkedin_queens_solver.ui import QueensUI

            self.queens_window = tk.Toplevel(self.root)
            self.queens_window.protocol("WM_DELETE_WINDOW", self._on_queens_close)
            QueensUI(self.queens_window)
            self.queens_btn.config(state="disabled")
            self.status_label.config(text="Queens solver launched.")
            self._hide_home()
        except Exception as exc:
            self._show_home()
            self.status_label.config(text=f"Error launching Queens: {exc}")

    def _on_queens_close(self):
        if self.queens_window is not None and self.queens_window.winfo_exists():
            self.queens_window.destroy()
        self.queens_window = None
        self.queens_btn.config(state="normal")
        self.status_label.config(text="Queens window closed.")
        self._show_home()

    def launch_tango(self):
        try:
            if self.tango_window is not None and self.tango_window.winfo_exists():
                self.tango_window.focus_force()
                self.status_label.config(text="Tango window is already open.")
                self._hide_home()
                return

            from tango_solver.ui import TangoUI

            self.tango_window = tk.Toplevel(self.root)
            self.tango_window.protocol("WM_DELETE_WINDOW", self._on_tango_close)
            TangoUI(self.tango_window)
            self.tango_btn.config(state="disabled")
            self.status_label.config(text="Tango solver launched.")
            self._hide_home()
        except Exception as exc:
            self._show_home()
            self.status_label.config(text=f"Error launching Tango: {exc}")

    def _on_tango_close(self):
        if self.tango_window is not None and self.tango_window.winfo_exists():
            self.tango_window.destroy()
        self.tango_window = None
        self.tango_btn.config(state="normal")
        self.status_label.config(text="Tango window closed.")
        self._show_home()

    def launch_zip(self):
        try:
            if self.zip_window is not None and self.zip_window.winfo_exists():
                self.zip_window.focus_force()
                self.status_label.config(text="Zip window is already open.")
                self._hide_home()
                return

            from zip_solver.ui import ZipUI

            self.zip_window = tk.Toplevel(self.root)
            self.zip_window.protocol("WM_DELETE_WINDOW", self._on_zip_close)
            ZipUI(self.zip_window)
            self.zip_btn.config(state="disabled")
            self.status_label.config(text="Zip solver launched.")
            self._hide_home()
        except Exception as exc:
            self._show_home()
            self.status_label.config(text=f"Error launching Zip: {exc}")

    def _on_zip_close(self):
        if self.zip_window is not None and self.zip_window.winfo_exists():
            self.zip_window.destroy()
        self.zip_window = None
        self.zip_btn.config(state="normal")
        self.status_label.config(text="Zip window closed.")
        self._show_home()


def main():
    root = tk.Tk()
    PuzzleSolverHome(root)
    root.mainloop()


if __name__ == "__main__":
    main()

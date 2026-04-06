"""
Direct entry point for the Sudoku Solver application.
Starts the professional Sudoku UI without a separate home menu.
"""

import tkinter as tk

from sudoku_solver.ui import SudokuSolverUI


def main():
    root = tk.Tk()
    SudokuSolverUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

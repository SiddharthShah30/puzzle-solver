"""Tkinter UI for LinkedIn-style Queens puzzle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Set, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .solver import QueensPuzzleSolver


COLOR_PALETTE = {
    0: "#a58dc8",
    1: "#edbe86",
    2: "#8bb9eb",
    3: "#99c78a",
    4: "#b8b8b8",
    5: "#f7785f",
    6: "#c7d96e",
}


class LinkedInQueensUI:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("LinkedIn Queens Solver")
        self.root.geometry("1050x760")

        self.samples_dir = Path(__file__).parent / "samples"

        self.region_map: List[List[int]] = []
        self.size = 0
        self.cell_size = 70

        self.fixed_queens: Set[Tuple[int, int]] = set()
        self.blocked_cells: Set[Tuple[int, int]] = set()
        self.solution_cells: Set[Tuple[int, int]] = set()

        self._setup_ui()
        self.load_sample("linkedin_queens_7x7.json")

    def _setup_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(outer, text="LinkedIn Queens Puzzle", font=("Helvetica", 16, "bold"))
        title.pack(anchor="w")

        rule_text = (
            "Rules: 1 queen per row, column, and color region. "
            "Queens cannot touch, even diagonally.\n"
            "Click cycle: Empty -> X -> Queen -> Empty"
        )
        self.rule_label = ttk.Label(outer, text=rule_text, font=("Helvetica", 10))
        self.rule_label.pack(anchor="w", pady=(4, 10))

        content = ttk.Frame(outer)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(content, text="Board", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(left, width=560, height=560, bg="#ffffff")
        self.canvas.pack(padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        right = ttk.LabelFrame(content, text="Controls", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        ttk.Button(right, text="Solve", command=self.solve).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Clear Marks", command=self.clear_marks).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Reset Sample", command=lambda: self.load_sample("linkedin_queens_7x7.json")).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load Puzzle JSON", command=self.load_puzzle_json).pack(fill=tk.X, pady=4)

        self.status = ttk.Label(right, text="Ready", wraplength=300)
        self.status.pack(fill=tk.X, pady=(14, 0))

    def load_sample(self, filename: str):
        path = self.samples_dir / filename
        if not path.exists():
            messagebox.showerror("Missing Sample", f"Could not find {filename}")
            return
        self._load_from_file(path)

    def load_puzzle_json(self):
        file_path = filedialog.askopenfilename(
            defaultdir=self.samples_dir,
            filetypes=[("JSON files", "*.json")],
        )
        if not file_path:
            return
        self._load_from_file(Path(file_path))

    def _load_from_file(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.region_map = data["regions"]
        self.size = len(self.region_map)
        self.fixed_queens = set(tuple(pos) for pos in data.get("fixed_queens", []))
        self.blocked_cells = set(tuple(pos) for pos in data.get("blocked", []))
        self.solution_cells = set()

        self.cell_size = max(40, min(78, 560 // self.size))
        self._draw_board()
        self.status.config(text=f"Loaded {path.name} ({self.size}x{self.size})")

    def _draw_board(self):
        self.canvas.delete("all")
        board_pixels = self.cell_size * self.size
        self.canvas.config(width=board_pixels, height=board_pixels)

        for r in range(self.size):
            for c in range(self.size):
                x1 = c * self.cell_size
                y1 = r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                rid = self.region_map[r][c]
                fill = COLOR_PALETTE.get(rid, "#dddddd")
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="#242424", width=1)

                if (r, c) in self.blocked_cells:
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text="X",
                        fill="#2d2d2d",
                        font=("Helvetica", max(12, self.cell_size // 3), "bold"),
                    )
                if (r, c) in self.fixed_queens:
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text="♛",
                        fill="#111111",
                        font=("Helvetica", max(14, self.cell_size // 2), "bold"),
                    )
                if (r, c) in self.solution_cells:
                    self.canvas.create_oval(x1 + 4, y1 + 4, x2 - 4, y2 - 4, outline="#0b5ed7", width=2)

    def on_canvas_click(self, event):
        if self.size == 0:
            return

        col = event.x // self.cell_size
        row = event.y // self.cell_size

        if not (0 <= row < self.size and 0 <= col < self.size):
            return

        cell = (row, col)
        self.solution_cells.clear()

        # Tap cycle: empty -> X -> queen -> empty
        if cell in self.fixed_queens:
            self.fixed_queens.remove(cell)
        elif cell in self.blocked_cells:
            self.blocked_cells.remove(cell)
            self.fixed_queens.add(cell)
        else:
            self.blocked_cells.add(cell)

        # queen and X cannot coexist
        if cell in self.fixed_queens and cell in self.blocked_cells:
            self.blocked_cells.remove(cell)

        self._draw_board()

    def clear_marks(self):
        self.fixed_queens.clear()
        self.blocked_cells.clear()
        self.solution_cells.clear()
        self._draw_board()
        self.status.config(text="Cleared all marks")

    def solve(self):
        try:
            solver = QueensPuzzleSolver(
                region_map=self.region_map,
                fixed_queens=list(self.fixed_queens),
                blocked_cells=set(self.blocked_cells),
            )
            if solver.solve():
                sol = solver.get_solution_board()
                self.solution_cells = {
                    (r, c)
                    for r in range(self.size)
                    for c in range(self.size)
                    if sol[r][c] == 1
                }
                self.fixed_queens = set(self.solution_cells)
                self.blocked_cells = {
                    (r, c)
                    for r in range(self.size)
                    for c in range(self.size)
                    if (r, c) not in self.fixed_queens
                }
                stats = solver.get_stats()
                self.status.config(text=f"Solved in {stats['time']:.4f}s with {stats['moves']} placements")
            else:
                self.status.config(text="No valid solution for current marks")
                messagebox.showwarning("No Solution", "No valid arrangement fits the current X/Queen marks.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

        self._draw_board()

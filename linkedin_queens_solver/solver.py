"""Queens puzzle solver for LinkedIn-style colored region puzzles.

Rules:
- Exactly one queen per row.
- Exactly one queen per column.
- Exactly one queen per color region.
- Queens cannot touch each other (including diagonal adjacency).
- User-marked X cells are treated as blocked.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
import time


class QueensPuzzleSolver:
    def __init__(
        self,
        region_map: List[List[int]],
        fixed_queens: Optional[List[Tuple[int, int]]] = None,
        blocked_cells: Optional[Set[Tuple[int, int]]] = None,
    ):
        self.region_map = region_map
        self.size = len(region_map)
        if self.size == 0 or any(len(row) != self.size for row in region_map):
            raise ValueError("region_map must be a non-empty square grid")

        self.fixed_queens = set(fixed_queens or [])
        self.blocked_cells = set(blocked_cells or set())

        self.region_cells: Dict[int, List[Tuple[int, int]]] = {}
        for r in range(self.size):
            for c in range(self.size):
                rid = self.region_map[r][c]
                self.region_cells.setdefault(rid, []).append((r, c))

        if len(self.region_cells) != self.size:
            raise ValueError(
                f"Puzzle must have exactly {self.size} regions, found {len(self.region_cells)}"
            )

        self.solution_positions: List[Tuple[int, int]] = []
        self.solve_time = 0.0
        self.moves = 0

    def _is_touching(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        return abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1

    def _validate_fixed_queens(self) -> bool:
        used_rows = set()
        used_cols = set()
        used_regions = set()

        for r, c in self.fixed_queens:
            if not (0 <= r < self.size and 0 <= c < self.size):
                return False
            if (r, c) in self.blocked_cells:
                return False

            rid = self.region_map[r][c]
            if r in used_rows or c in used_cols or rid in used_regions:
                return False

            for qr, qc in self.fixed_queens:
                if (qr, qc) != (r, c) and self._is_touching(r, c, qr, qc):
                    return False

            used_rows.add(r)
            used_cols.add(c)
            used_regions.add(rid)

        return True

    def solve(self) -> bool:
        start = time.time()
        self.moves = 0

        if not self._validate_fixed_queens():
            self.solve_time = time.time() - start
            return False

        row_to_fixed = {r: c for r, c in self.fixed_queens}

        used_rows = set(r for r, _ in self.fixed_queens)
        used_cols = set(c for _, c in self.fixed_queens)
        used_regions = set(self.region_map[r][c] for r, c in self.fixed_queens)
        queens = list(self.fixed_queens)

        rows_to_fill = [r for r in range(self.size) if r not in row_to_fixed]

        def backtrack(row_index: int) -> bool:
            if row_index == len(rows_to_fill):
                return len(queens) == self.size

            row = rows_to_fill[row_index]

            for col in range(self.size):
                if (row, col) in self.blocked_cells:
                    continue
                if col in used_cols:
                    continue

                rid = self.region_map[row][col]
                if rid in used_regions:
                    continue

                touching = False
                for qr, qc in queens:
                    if self._is_touching(row, col, qr, qc):
                        touching = True
                        break
                if touching:
                    continue

                self.moves += 1
                queens.append((row, col))
                used_rows.add(row)
                used_cols.add(col)
                used_regions.add(rid)

                if backtrack(row_index + 1):
                    return True

                queens.pop()
                used_rows.remove(row)
                used_cols.remove(col)
                used_regions.remove(rid)

            return False

        solved = backtrack(0)
        self.solve_time = time.time() - start

        if solved:
            self.solution_positions = sorted(queens)
        else:
            self.solution_positions = []

        return solved

    def get_solution_board(self) -> List[List[int]]:
        board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        for r, c in self.solution_positions:
            board[r][c] = 1
        return board

    def get_stats(self) -> dict:
        return {
            "time": self.solve_time,
            "moves": self.moves,
            "size": self.size,
        }

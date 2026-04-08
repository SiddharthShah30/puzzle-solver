"""Solver for Tango (binary puzzle / Takuzu-style) grids.

Rules:
- Every cell is either symbol 1 or symbol 2.
- No more than two equal symbols may be adjacent horizontally or vertically.
- Each row and each column must contain the same number of symbol 1 and symbol 2.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import time


class TangoPuzzleSolver:
    def __init__(self, clues: List[List[int]]):
        self.initial_board = [row[:] for row in clues]
        self.rows = len(clues)
        self.cols = len(clues[0]) if clues else 0

        if self.rows == 0 or self.cols == 0 or any(len(row) != self.cols for row in clues):
            raise ValueError("Clues must be a non-empty rectangular grid")
        if self.rows % 2 != 0 or self.cols % 2 != 0:
            raise ValueError("Tango board dimensions must both be even")

        valid_values = {0, 1, 2}
        for row in clues:
            for value in row:
                if value not in valid_values:
                    raise ValueError("Grid values must be 0 (empty), 1, or 2")

        self.solution: Optional[List[List[int]]] = None
        self.solution_count = 0
        self.solve_time = 0.0
        self.moves = 0

    def solve(self, verify_unique: bool = False) -> bool:
        start = time.time()
        self.moves = 0
        self.solution = None
        self.solution_count = 0

        board = [row[:] for row in self.initial_board]
        if not self._propagate(board):
            self.solve_time = time.time() - start
            return False

        solutions: List[List[List[int]]] = []
        limit = 2 if verify_unique else 1

        def backtrack(current: List[List[int]]) -> None:
            if len(solutions) >= limit:
                return

            cell = self._select_cell_with_smallest_domain(current)
            if cell is None:
                solutions.append([row[:] for row in current])
                return

            r, c, domain = cell
            for value in domain:
                self.moves += 1
                nxt = [row[:] for row in current]
                nxt[r][c] = value
                if not self._propagate(nxt):
                    continue
                backtrack(nxt)
                if len(solutions) >= limit:
                    return

        backtrack(board)

        self.solution_count = len(solutions)
        if solutions:
            self.solution = solutions[0]

        self.solve_time = time.time() - start

        if not solutions:
            return False
        if verify_unique and self.solution_count != 1:
            return False
        return True

    def _line_valid(self, line: List[int]) -> bool:
        half = len(line) // 2
        count1 = sum(1 for v in line if v == 1)
        count2 = sum(1 for v in line if v == 2)
        if count1 > half or count2 > half:
            return False

        for i in range(len(line) - 2):
            a, b, c = line[i], line[i + 1], line[i + 2]
            if a != 0 and a == b == c:
                return False

        if 0 not in line and (count1 != half or count2 != half):
            return False

        return True

    def _apply_line_rules(self, line: List[int]) -> Tuple[bool, bool]:
        changed = False
        line_len = len(line)
        half = line_len // 2

        count1 = sum(1 for v in line if v == 1)
        count2 = sum(1 for v in line if v == 2)

        if count1 > half or count2 > half:
            return False, changed

        if count1 == half:
            for i in range(line_len):
                if line[i] == 0:
                    line[i] = 2
                    changed = True
        elif count2 == half:
            for i in range(line_len):
                if line[i] == 0:
                    line[i] = 1
                    changed = True

        for i in range(line_len - 2):
            a, b, c = line[i], line[i + 1], line[i + 2]

            if a != 0 and a == b and c == 0:
                line[i + 2] = 3 - a
                changed = True
            elif b != 0 and b == c and a == 0:
                line[i] = 3 - b
                changed = True
            elif a != 0 and a == c and b == 0:
                line[i + 1] = 3 - a
                changed = True

            if line[i] != 0 and line[i] == line[i + 1] == line[i + 2]:
                return False, changed

        if not self._line_valid(line):
            return False, changed

        return True, changed

    def _propagate(self, board: List[List[int]]) -> bool:
        changed = True
        while changed:
            changed = False

            for r in range(self.rows):
                row = board[r][:]
                ok, row_changed = self._apply_line_rules(row)
                if not ok:
                    return False
                if row_changed:
                    board[r] = row
                    changed = True

            for c in range(self.cols):
                col = [board[r][c] for r in range(self.rows)]
                ok, col_changed = self._apply_line_rules(col)
                if not ok:
                    return False
                if col_changed:
                    for r in range(self.rows):
                        board[r][c] = col[r]
                    changed = True

            for r in range(self.rows):
                if not self._line_valid(board[r]):
                    return False
            for c in range(self.cols):
                if not self._line_valid([board[r][c] for r in range(self.rows)]):
                    return False

        return True

    def _domain_for_cell(self, board: List[List[int]], r: int, c: int) -> List[int]:
        if board[r][c] != 0:
            return []

        domain: List[int] = []
        for value in (1, 2):
            trial = [row[:] for row in board]
            trial[r][c] = value
            if self._propagate(trial):
                domain.append(value)
        return domain

    def _select_cell_with_smallest_domain(self, board: List[List[int]]) -> Optional[Tuple[int, int, List[int]]]:
        best: Optional[Tuple[int, int, List[int]]] = None

        for r in range(self.rows):
            for c in range(self.cols):
                if board[r][c] != 0:
                    continue
                domain = self._domain_for_cell(board, r, c)
                if not domain:
                    return (r, c, domain)
                if best is None or len(domain) < len(best[2]):
                    best = (r, c, domain)
                    if len(domain) == 1:
                        return best

        return best

    def get_solution_board(self) -> List[List[int]]:
        if self.solution is None:
            raise ValueError("No solution available")
        return [row[:] for row in self.solution]

    def get_stats(self) -> dict:
        return {
            "time": self.solve_time,
            "moves": self.moves,
            "rows": self.rows,
            "cols": self.cols,
            "solutions_found": self.solution_count,
        }

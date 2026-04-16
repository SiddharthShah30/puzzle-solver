"""Solver for Zip single-path sequential puzzles.

Rules:
- Draw one continuous orthogonal path.
- Visit numbered clues in ascending order 1..N.
- Cover every cell exactly once.
- Respect optional wall barriers between adjacent cells.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Set, Tuple
import time

Coordinate = Tuple[int, int]


class ZipPuzzleSolver:
    def __init__(
        self,
        clues: List[List[int]],
        h_walls: Optional[List[List[int]]] = None,
        v_walls: Optional[List[List[int]]] = None,
    ):
        self.initial_board = [row[:] for row in clues]
        self.rows = len(clues)
        self.cols = len(clues[0]) if clues else 0

        if self.rows == 0 or self.cols == 0 or any(len(row) != self.cols for row in clues):
            raise ValueError("Clues must be a non-empty rectangular grid")

        for row in clues:
            for value in row:
                if value < 0:
                    raise ValueError("Grid values must be 0 or positive integers")

        self.h_walls = self._normalize_h_walls(h_walls)
        self.v_walls = self._normalize_v_walls(v_walls)

        self.sequence_positions = self._collect_sequence_positions(clues)
        if not self.sequence_positions:
            raise ValueError("At least one numbered clue is required")
        labels = sorted(self.sequence_positions.keys())
        if labels != list(range(1, len(labels) + 1)):
            raise ValueError("Zip requires labels 1..N, each appearing exactly once")
        if len(labels) < 2:
            raise ValueError("Zip requires at least two clues (1 and 2)")

        self.sequence_order = labels
        self.start_cell = self.sequence_positions[labels[0]]
        self.end_cell = self.sequence_positions[labels[-1]]

        self.solution: Optional[List[List[int]]] = None
        self.solution_path: Optional[List[Coordinate]] = None
        self.solution_count = 0
        self.solve_time = 0.0
        self.moves = 0

    def _normalize_h_walls(self, h_walls: Optional[List[List[int]]]) -> List[List[int]]:
        expected_cols = max(0, self.cols - 1)
        if h_walls is None:
            return [[0 for _ in range(expected_cols)] for _ in range(self.rows)]
        if len(h_walls) != self.rows or any(len(row) != expected_cols for row in h_walls):
            raise ValueError("h_walls must have shape rows x (cols-1)")
        out: List[List[int]] = []
        for row in h_walls:
            norm_row: List[int] = []
            for value in row:
                if value not in (0, 1):
                    raise ValueError("Wall values must be 0 or 1")
                norm_row.append(int(value))
            out.append(norm_row)
        return out

    def _normalize_v_walls(self, v_walls: Optional[List[List[int]]]) -> List[List[int]]:
        expected_rows = max(0, self.rows - 1)
        if v_walls is None:
            return [[0 for _ in range(self.cols)] for _ in range(expected_rows)]
        if len(v_walls) != expected_rows or any(len(row) != self.cols for row in v_walls):
            raise ValueError("v_walls must have shape (rows-1) x cols")
        out: List[List[int]] = []
        for row in v_walls:
            norm_row: List[int] = []
            for value in row:
                if value not in (0, 1):
                    raise ValueError("Wall values must be 0 or 1")
                norm_row.append(int(value))
            out.append(norm_row)
        return out

    def _collect_sequence_positions(self, clues: List[List[int]]) -> Dict[int, Coordinate]:
        positions: Dict[int, Coordinate] = {}
        for r, row in enumerate(clues):
            for c, value in enumerate(row):
                if value == 0:
                    continue
                if value in positions:
                    raise ValueError(f"Number {value} appears more than once")
                positions[value] = (r, c)
        return positions

    def _is_blocked(self, a: Coordinate, b: Coordinate) -> bool:
        ar, ac = a
        br, bc = b
        if ar == br:
            left = min(ac, bc)
            return self.h_walls[ar][left] == 1
        top = min(ar, br)
        return self.v_walls[top][ac] == 1

    def _neighbors(self, r: int, c: int) -> List[Coordinate]:
        out = []
        if r > 0 and not self._is_blocked((r, c), (r - 1, c)):
            out.append((r - 1, c))
        if r + 1 < self.rows and not self._is_blocked((r, c), (r + 1, c)):
            out.append((r + 1, c))
        if c > 0 and not self._is_blocked((r, c), (r, c - 1)):
            out.append((r, c - 1))
        if c + 1 < self.cols and not self._is_blocked((r, c), (r, c + 1)):
            out.append((r, c + 1))
        return out

    def _manhattan(self, a: Coordinate, b: Coordinate) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])


    def _shortest_unvisited_distance(
        self,
        start: Coordinate,
        target: Coordinate,
        visited: Set[Coordinate],
    ) -> Optional[int]:
        if start == target:
            return 0
        queue: Deque[Tuple[Coordinate, int]] = deque([(start, 0)])
        seen = {start}
        while queue:
            (r, c), dist = queue.popleft()
            for nr, nc in self._neighbors(r, c):
                nxt = (nr, nc)
                if nxt in seen:
                    continue
                if nxt in visited and nxt != target:
                    continue
                if nxt == target:
                    return dist + 1
                seen.add(nxt)
                queue.append((nxt, dist + 1))
        return None

    def _open_component_check(self, current: Coordinate, visited: Set[Coordinate]) -> bool:
        open_cells = {(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in visited}
        if not open_cells:
            return True

        # Any unvisited cells must remain connected to the current frontier.
        starts = [n for n in self._neighbors(current[0], current[1]) if n in open_cells]
        if not starts:
            return False

        queue: Deque[Coordinate] = deque([starts[0]])
        seen = {starts[0]}
        while queue:
            r, c = queue.popleft()
            for nr, nc in self._neighbors(r, c):
                nxt = (nr, nc)
                if nxt in open_cells and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen == open_cells

    def _can_step_to(self, nxt: Coordinate, visited: Set[Coordinate], required_next_label: int) -> bool:
        if nxt in visited:
            return False
        value = self.initial_board[nxt[0]][nxt[1]]
        if value == 0:
            return True
        return value == required_next_label

    def _candidate_order(self, current: Coordinate, visited: Set[Coordinate], required_next_label: int) -> List[Coordinate]:
        target = self.sequence_positions[required_next_label]
        candidates = [n for n in self._neighbors(current[0], current[1]) if self._can_step_to(n, visited, required_next_label)]
        candidates.sort(
            key=lambda pos: (
                0 if self.initial_board[pos[0]][pos[1]] == required_next_label else 1,
                sum(1 for nn in self._neighbors(pos[0], pos[1]) if nn not in visited),
                self._manhattan(pos, target),
            )
        )
        return candidates

    def _solve_sequential(self, verify_unique: bool = False) -> bool:
        start_time = time.time()
        self.moves = 0
        self.solution = None
        self.solution_path = None
        self.solution_count = 0

        total_cells = self.rows * self.cols
        limit = 2 if verify_unique else 1
        solutions: List[List[List[int]]] = []

        visited: Set[Coordinate] = {self.start_cell}
        path: List[Coordinate] = [self.start_cell]

        def dfs(cell: Coordinate, index: int):
            if len(solutions) >= limit:
                return

            if len(path) == total_cells:
                if cell == self.end_cell and index == len(self.sequence_order) - 1:
                    solution_board = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
                    for step, (rr, cc) in enumerate(path, start=1):
                        solution_board[rr][cc] = step
                    solutions.append(solution_board)
                    self.solution_path = path[:]
                return

            required_next_label = self.sequence_order[index + 1] if index + 1 < len(self.sequence_order) else self.sequence_order[index]

            # Must still be able to reach the next required clue.
            target = self.sequence_positions[required_next_label]
            if self._shortest_unvisited_distance(cell, target, visited) is None:
                return

            candidates = self._candidate_order(cell, visited, required_next_label)

            for nxt in candidates:
                nxt_index = index
                nxt_value = self.initial_board[nxt[0]][nxt[1]]
                if nxt_value != 0 and index + 1 < len(self.sequence_order):
                    if nxt_value != self.sequence_order[index + 1]:
                        continue
                    nxt_index = index + 1

                visited.add(nxt)
                path.append(nxt)
                self.moves += 1

                # Dead-end prune: if not finished, there must be room to continue.
                if len(path) < total_cells:
                    onward = [nn for nn in self._neighbors(nxt[0], nxt[1]) if nn not in visited]
                    if not onward:
                        path.pop()
                        visited.remove(nxt)
                        continue

                if self._open_component_check(nxt, visited):
                    dfs(nxt, nxt_index)

                path.pop()
                visited.remove(nxt)
                if len(solutions) >= limit:
                    return

        dfs(self.start_cell, 0)

        self.solution_count = len(solutions)
        if solutions:
            self.solution = solutions[0]
            if self.solution_path is None and self.solution is not None:
                ordered: List[Tuple[int, Coordinate]] = []
                for r in range(self.rows):
                    for c in range(self.cols):
                        value = self.solution[r][c]
                        if value > 0:
                            ordered.append((value, (r, c)))
                ordered.sort(key=lambda item: item[0])
                self.solution_path = [cell for _, cell in ordered]

        self.solve_time = time.time() - start_time
        if not solutions:
            return False
        if verify_unique and self.solution_count != 1:
            return False
        return True

    def solve(self, verify_unique: bool = False) -> bool:
        return self._solve_sequential(verify_unique=verify_unique)

    def get_solution_board(self) -> List[List[int]]:
        if self.solution is None:
            raise ValueError("No solution available")
        return [row[:] for row in self.solution]

    def get_solution_path(self) -> List[Coordinate]:
        if self.solution_path is None:
            raise ValueError("No solution path available")
        return list(self.solution_path)

    def get_stats(self) -> dict:
        return {
            "time": self.solve_time,
            "moves": self.moves,
            "rows": self.rows,
            "cols": self.cols,
            "solutions_found": self.solution_count,
            "rule_set": "sequential-single-path",
        }

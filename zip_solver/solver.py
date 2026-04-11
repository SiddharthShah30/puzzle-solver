"""Solver for Zip, a Numberlink-style path puzzle.

Rules:
- Each numbered clue must appear exactly twice.
- Matching numbers must be connected by an orthogonal path.
- Paths cannot cross.
- Every cell must belong to exactly one path, so there are no blanks.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Deque, Dict, List, Optional, Set, Tuple
import time

Coordinate = Tuple[int, int]


class ZipPuzzleSolver:
    def __init__(self, clues: List[List[int]]):
        self.initial_board = [row[:] for row in clues]
        self.rows = len(clues)
        self.cols = len(clues[0]) if clues else 0

        if self.rows == 0 or self.cols == 0 or any(len(row) != self.cols for row in clues):
            raise ValueError("Clues must be a non-empty rectangular grid")

        for row in clues:
            for value in row:
                if value < 0:
                    raise ValueError("Grid values must be 0 or positive integers")

        self.pairs: Dict[int, List[Coordinate]] = self._collect_pairs(clues)
        if not self.pairs:
            raise ValueError("At least one numbered pair is required")
        for label, cells in self.pairs.items():
            if len(cells) != 2:
                raise ValueError(f"Number {label} must appear exactly twice")

        self.solution: Optional[List[List[int]]] = None
        self.solution_count = 0
        self.solve_time = 0.0
        self.moves = 0

    def _collect_pairs(self, clues: List[List[int]]) -> Dict[int, List[Coordinate]]:
        pairs: Dict[int, List[Coordinate]] = {}
        for r, row in enumerate(clues):
            for c, value in enumerate(row):
                if value == 0:
                    continue
                pairs.setdefault(value, []).append((r, c))
        return pairs

    def _neighbors(self, r: int, c: int) -> List[Coordinate]:
        out = []
        if r > 0:
            out.append((r - 1, c))
        if r + 1 < self.rows:
            out.append((r + 1, c))
        if c > 0:
            out.append((r, c - 1))
        if c + 1 < self.cols:
            out.append((r, c + 1))
        return out

    def _manhattan(self, a: Coordinate, b: Coordinate) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _label_order(self, board: List[List[int]], remaining: Set[int]) -> List[int]:
        scored: List[Tuple[int, int, int]] = []
        for label in remaining:
            distance = self._shortest_path_length(board, label)
            if distance is None:
                return []
            scored.append((distance, label, self._pair_span(label)))
        scored.sort(key=lambda item: (item[0], item[2]))
        return [label for _, label, _ in scored]

    def _pair_span(self, label: int) -> int:
        a, b = self.pairs[label]
        return self._manhattan(a, b)

    def _shortest_path_length(self, board: List[List[int]], label: int) -> Optional[int]:
        start, end = self.pairs[label]
        queue: Deque[Tuple[Coordinate, int]] = deque([(start, 1)])
        seen = {start}

        while queue:
            (r, c), dist = queue.popleft()
            if (r, c) == end:
                return dist
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) in seen:
                    continue
                value = board[nr][nc]
                if value == 0 or (nr, nc) == end:
                    seen.add((nr, nc))
                    queue.append(((nr, nc), dist + 1))
        return None

    def _future_feasible(self, board: List[List[int]], remaining: Set[int]) -> bool:
        if not remaining:
            return all(value != 0 for row in board for value in row)

        endpoints = [pos for label in remaining for pos in self.pairs[label]]
        if not endpoints:
            return False

        # Every remaining pair must still have a possible connecting route.
        for label in remaining:
            if self._shortest_path_length(board, label) is None:
                return False

        # Every empty cell must remain reachable from at least one remaining endpoint.
        reachable: Set[Coordinate] = set()
        queue: Deque[Coordinate] = deque(endpoints)
        seen: Set[Coordinate] = set(endpoints)

        while queue:
            r, c = queue.popleft()
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) in seen:
                    continue
                value = board[nr][nc]
                if value == 0 or (nr, nc) in endpoints:
                    seen.add((nr, nc))
                    queue.append((nr, nc))
                    if value == 0:
                        reachable.add((nr, nc))

        for r in range(self.rows):
            for c in range(self.cols):
                if board[r][c] == 0 and (r, c) not in reachable:
                    return False

        return True

    def _board_is_final_valid(self, board: List[List[int]]) -> bool:
        if any(0 in row for row in board):
            return False

        for label, endpoints in self.pairs.items():
            cells = [(r, c) for r in range(self.rows) for c in range(self.cols) if board[r][c] == label]
            if len(cells) < 2:
                return False

            allowed = set(cells)
            start, end = endpoints
            if board[start[0]][start[1]] != label or board[end[0]][end[1]] != label:
                return False

            # Connected component check.
            queue: Deque[Coordinate] = deque([start])
            seen = {start}
            while queue:
                r, c = queue.popleft()
                for nr, nc in self._neighbors(r, c):
                    if (nr, nc) in seen:
                        continue
                    if (nr, nc) in allowed:
                        seen.add((nr, nc))
                        queue.append((nr, nc))
            if seen != allowed:
                return False

            degrees = []
            for r, c in cells:
                degree = sum(1 for nr, nc in self._neighbors(r, c) if board[nr][nc] == label)
                degrees.append(degree)
                if (r, c) in endpoints:
                    if degree != 1:
                        return False
                elif degree != 2:
                    return False

        return True

    def _generate_paths(
        self,
        board: List[List[int]],
        label: int,
        remaining: Set[int],
        limit: int = 250,
    ) -> List[List[Coordinate]]:
        start, end = self.pairs[label]
        free_cells = sum(1 for row in board for value in row if value == 0)
        is_last = len(remaining) == 1
        target_length = free_cells + 2 if is_last else None
        paths: List[List[Coordinate]] = []
        visited: Set[Coordinate] = {start}
        path: List[Coordinate] = [start]

        def allowed(cell: Coordinate) -> bool:
            if cell == start or cell == end:
                return True
            return board[cell[0]][cell[1]] == 0

        def degree_score(cell: Coordinate) -> Tuple[int, int, int]:
            if cell == end:
                return (-1, 0, 0)
            unvisited_degree = 0
            for nr, nc in self._neighbors(cell[0], cell[1]):
                if (nr, nc) in visited:
                    continue
                if allowed((nr, nc)):
                    unvisited_degree += 1
            return (unvisited_degree, self._manhattan(cell, end), cell[0] + cell[1])

        def dfs(cell: Coordinate):
            if len(paths) >= limit:
                return

            if cell == end:
                if target_length is not None and len(path) != target_length:
                    return
                candidate_board = [row[:] for row in board]
                for pr, pc in path:
                    candidate_board[pr][pc] = label
                if not is_last and not self._future_feasible(candidate_board, remaining - {label}):
                    return
                paths.append(path[:])
                return

            neighbors = [n for n in self._neighbors(cell[0], cell[1]) if n not in visited and allowed(n)]
            neighbors.sort(key=degree_score)

            for nxt in neighbors:
                visited.add(nxt)
                path.append(nxt)
                if target_length is None or len(path) <= target_length:
                    dfs(nxt)
                path.pop()
                visited.remove(nxt)
                if len(paths) >= limit:
                    return

        dfs(start)
        return paths

    def solve(self, verify_unique: bool = False) -> bool:
        start_time = time.time()
        self.moves = 0
        self.solution = None
        self.solution_count = 0

        board = [row[:] for row in self.initial_board]
        remaining = set(self.pairs.keys())
        limit = 2 if verify_unique else 1
        solutions: List[List[List[int]]] = []

        def recurse(current_board: List[List[int]], remaining_labels: Set[int]):
            if len(solutions) >= limit:
                return

            if not remaining_labels:
                if self._board_is_final_valid(current_board):
                    solutions.append([row[:] for row in current_board])
                return

            label_order = self._label_order(current_board, remaining_labels)
            if not label_order:
                return
            label = label_order[0]

            paths = self._generate_paths(current_board, label, remaining_labels, limit=300)
            if not paths:
                return

            for path in paths:
                self.moves += 1
                next_board = [row[:] for row in current_board]
                for r, c in path:
                    next_board[r][c] = label
                next_remaining = set(remaining_labels)
                next_remaining.remove(label)
                if not self._future_feasible(next_board, next_remaining):
                    continue
                recurse(next_board, next_remaining)
                if len(solutions) >= limit:
                    return

        if self._future_feasible(board, remaining):
            recurse(board, remaining)

        self.solution_count = len(solutions)
        if solutions:
            self.solution = solutions[0]

        self.solve_time = time.time() - start_time
        if not solutions:
            return False
        if verify_unique and self.solution_count != 1:
            return False
        return True

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

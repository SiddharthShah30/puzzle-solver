"""
Sudoku Solver using Backtracking with Constraint Propagation.
Supports square, rectangular, and custom irregular region layouts.
"""

import time
from typing import Dict, List, Optional, Set, Tuple


class SudokuSolver:
    def __init__(
        self,
        board: List[List[int]],
        size: Optional[int] = None,
        region_map: Optional[List[List[int]]] = None,
        region_shape: Optional[Tuple[int, int]] = None,
    ):
        """
        Initialize Sudoku Solver.

        Args:
            board: 2D list representing the sudoku board (0 = empty)
            size: Sudoku size (any positive integer).
            region_map: Optional 2D list mapping each cell to a region id.
            region_shape: Optional (region_rows, region_cols) for rectangular regions.
        """
        if size is None:
            size = len(board)

        self.original_board = [row[:] for row in board]
        self.board = [row[:] for row in board]
        self.size = size
        self.region_shape = region_shape
        self.solve_time = 0
        self.moves_count = 0
        self.constraints = None

        self._validate_board_shape()
        self.region_map = self._normalize_region_map(region_map)
        self.region_cells = self._build_region_cells()

        self._initialize_constraints()

    def _validate_board_shape(self):
        if len(self.board) != self.size or any(len(row) != self.size for row in self.board):
            raise ValueError(f"Board must be a {self.size}x{self.size} grid")

    def _standard_region_map(self) -> List[List[int]]:
        if self.region_shape is not None:
            region_rows, region_cols = self.region_shape
            if region_rows <= 0 or region_cols <= 0:
                raise ValueError("Region dimensions must be positive integers")
            if region_rows * region_cols != self.size:
                raise ValueError(
                    f"For rectangular regions, size must equal region_rows * region_cols; got {self.size} and {region_rows}x{region_cols}"
                )
        else:
            region_rows = int(self.size ** 0.5)
            region_cols = region_rows
            if region_rows * region_cols != self.size:
                raise ValueError(
                    "Standard regions require a square grid size. Provide region_shape for rectangular layouts or region_map for irregular layouts."
                )

        regions_across = self.size // region_cols

        return [
            [
                (row // region_rows) * regions_across + (col // region_cols)
                for col in range(self.size)
            ]
            for row in range(self.size)
        ]

    def _normalize_region_map(self, region_map: Optional[List[List[int]]]) -> List[List[int]]:
        if region_map is None:
            return self._standard_region_map()

        if len(region_map) != self.size or any(len(row) != self.size for row in region_map):
            raise ValueError(f"Region map must be a {self.size}x{self.size} grid")

        return [[int(cell) for cell in row] for row in region_map]

    def _build_region_cells(self) -> Dict[int, Set[Tuple[int, int]]]:
        region_cells: Dict[int, Set[Tuple[int, int]]] = {}

        for row in range(self.size):
            for col in range(self.size):
                region_id = self.region_map[row][col]
                region_cells.setdefault(region_id, set()).add((row, col))

        if len(region_cells) != self.size:
            raise ValueError(
                f"Region map must contain exactly {self.size} regions; found {len(region_cells)}"
            )

        for region_id, cells in region_cells.items():
            if len(cells) != self.size:
                raise ValueError(
                    f"Region {region_id} must contain exactly {self.size} cells; found {len(cells)}"
                )

        return region_cells

    def _region_neighbors(self, row: int, col: int) -> Set[Tuple[int, int]]:
        region_id = self.region_map[row][col]
        return self.region_cells[region_id]

    def _initialize_constraints(self):
        """Initialize constraint sets for each cell"""
        self.constraints = [[set(range(1, self.size + 1)) for _ in range(self.size)]
                           for _ in range(self.size)]

        # Remove constraints based on initial board
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] != 0:
                    self._update_constraints(i, j, self.board[i][j])

    def _update_constraints(self, row: int, col: int, value: int):
        """Update constraints when a value is placed"""
        # Clear constraints for this cell
        self.constraints[row][col] = set()

        # Remove from row constraints
        for c in range(self.size):
            self.constraints[row][c].discard(value)

        # Remove from column constraints
        for r in range(self.size):
            self.constraints[r][col].discard(value)

        # Remove from region constraints
        for r, c in self._region_neighbors(row, col):
            self.constraints[r][c].discard(value)

    def _get_next_cell(self) -> Optional[Tuple[int, int]]:
        """Get the next empty cell with minimum remaining values (MRV heuristic)"""
        min_choices = self.size + 1
        best_cell = None
        
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == 0:
                    choices = len(self.constraints[i][j])
                    if choices == 0:
                        return None  # No valid choices - contradiction
                    if choices < min_choices:
                        min_choices = choices
                        best_cell = (i, j)
        
        return best_cell

    def _is_valid(self, row: int, col: int, value: int) -> bool:
        """Check if placing value at (row, col) is valid"""
        # Check row
        if value in self.board[row]:
            return False
        
        # Check column
        if value in [self.board[r][col] for r in range(self.size)]:
            return False
        
        # Check region
        for r, c in self._region_neighbors(row, col):
            if self.board[r][c] == value:
                return False
        
        return True

    def _solve_recursive(self) -> bool:
        """Recursive backtracking with constraint propagation"""
        cell = self._get_next_cell()
        
        if cell is None:
            # Check if board is completely filled
            for i in range(self.size):
                for j in range(self.size):
                    if self.board[i][j] == 0:
                        return False
            return True
        
        row, col = cell
        
        # Try values in order of constraints (minimum remaining values first)
        for value in sorted(self.constraints[row][col]):
            if self._is_valid(row, col, value):
                # Save current state
                old_constraints = [[cell.copy() for cell in row_constraints] 
                                 for row_constraints in self.constraints]
                
                # Place value
                self.board[row][col] = value
                self.moves_count += 1
                self._update_constraints(row, col, value)
                
                # Recursive call
                if self._solve_recursive():
                    return True
                
                # Backtrack
                self.board[row][col] = 0
                self.constraints = old_constraints
        
        return False

    def solve(self) -> bool:
        """Solve the sudoku puzzle"""
        start_time = time.time()
        self.moves_count = 0
        
        self._initialize_constraints()
        result = self._solve_recursive()
        
        self.solve_time = time.time() - start_time
        return result

    def get_solution(self) -> List[List[int]]:
        """Return the solved board"""
        return self.board

    def get_stats(self) -> dict:
        """Return solving statistics"""
        return {
            'time': self.solve_time,
            'moves': self.moves_count,
            'board_size': self.size
        }

    def is_valid_sudoku(self) -> bool:
        """Check if current board is a valid sudoku"""
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] != 0:
                    value = self.board[i][j]
                    self.board[i][j] = 0
                    
                    if not self._is_valid(i, j, value):
                        self.board[i][j] = value
                        return False
                    
                    self.board[i][j] = value
        
        return True

    def reset(self):
        """Reset to original puzzle"""
        self.board = [row[:] for row in self.original_board]
        self._initialize_constraints()
        self.moves_count = 0
        self.solve_time = 0

"""
Sudoku Solver using Backtracking with Constraint Propagation
Supports sudoku sizes: 1x1, 4x4, 9x9, 16x16
"""

import time
from typing import List, Tuple, Set, Optional


class SudokuSolver:
    def __init__(self, board: List[List[int]], size: int = 9):
        """
        Initialize Sudoku Solver
        
        Args:
            board: 2D list representing the sudoku board (0 = empty)
            size: Sudoku size (9, 16, 4, 1)
        """
        self.original_board = [row[:] for row in board]
        self.board = [row[:] for row in board]
        self.size = size
        self.box_size = int(size ** 0.5)
        self.solve_time = 0
        self.moves_count = 0
        self.constraints = None
        
        # Validate size
        if size not in [1, 4, 9, 16]:
            raise ValueError(f"Sudoku size must be 1, 4, 9, or 16, got {size}")
        
        self._initialize_constraints()

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
        
        # Remove from box constraints
        box_row = (row // self.box_size) * self.box_size
        box_col = (col // self.box_size) * self.box_size
        for r in range(box_row, box_row + self.box_size):
            for c in range(box_col, box_col + self.box_size):
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
        
        # Check box
        box_row = (row // self.box_size) * self.box_size
        box_col = (col // self.box_size) * self.box_size
        for r in range(box_row, box_row + self.box_size):
            for c in range(box_col, box_col + self.box_size):
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

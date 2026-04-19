"""
Advanced Sudoku Solver UI with Keyboard Navigation
- Supports any grid size and irregular Sudoku
- Keyboard controls for easy input
- Post-solve verification for learning improvement
- Full tracking of solve accuracy
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import List, Optional, Tuple, Set
import hashlib
import json
from pathlib import Path
import string

from .solver import SudokuSolver
from .learner import SudokuLearner
from ui_theme import apply_app_theme
from ui_theme import apply_app_theme


class SudokuSolverUI:
    def __init__(self, root: tk.Tk, theme_name: str = "light"):
        self.root = root
        self.root.title("Complete Sudoku Solver - All Grids & Sizes")
        self.root.geometry("1400x950")
        self.theme_name = theme_name
        self.theme = apply_app_theme(self.root, theme_name)
        
        self.solver: Optional[SudokuSolver] = None
        self.learner = SudokuLearner()
        self.board_size = 9
        self.canvas_size = 500
        self.cell_size = self.canvas_size // self.board_size
        
        self.board: List[List[int]] = [[0] * 9 for _ in range(9)]
        self.original_board: List[List[int]] = [[0] * 9 for _ in range(9)]
        self.solution: List[List[int]] = []
        self.user_verified_correct = False
        self.region_shape: Optional[Tuple[int, int]] = None
        self.region_map: List[List[int]] = self._create_standard_region_map(self.board_size)
        
        self.solving = False
        self.solved = False
        self.selected_cell: Optional[Tuple[int, int]] = None
        self.selected_number = 0
        self.ui_input_locked = False
        
        # Get samples directory
        self.samples_dir = Path(__file__).parent / "samples"
        
        # Custom irregular grid support
        self.irregular_regions: List[Set[Tuple[int, int]]] = []
        
        self.setup_styles()
        self.setup_ui()
        self.bind_keyboard()
        self.root.focus_set()

    def setup_styles(self):
        """Setup a consistent ttk style theme."""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

    def refresh_theme(self, theme_name: str):
        self.theme_name = theme_name
        self.theme = apply_app_theme(self.root, theme_name)
        if hasattr(self, "canvas"):
            self.canvas.configure(bg=self.theme["canvas"])
            self.draw_board()

    def _create_standard_region_map(self, size: int) -> List[List[int]]:
        """Create the default square-region layout for standard Sudoku."""
        if self.region_shape is not None:
            region_rows, region_cols = self.region_shape
            if region_rows * region_cols != size:
                raise ValueError("Region rows and columns must multiply to the board size")
        else:
            region_rows = int(size ** 0.5)
            region_cols = region_rows
            if region_rows * region_cols != size:
                return [[row * size + col for col in range(size)] for row in range(size)]

        regions_across = size // region_cols
        return [
            [
                (row // region_rows) * regions_across + (col // region_cols)
                for col in range(size)
            ]
            for row in range(size)
        ]

    def _is_valid_region_map(self, region_map: List[List[int]], size: int) -> bool:
        if len(region_map) != size or any(len(row) != size for row in region_map):
            return False

        region_counts = {}
        for row in region_map:
            for region_id in row:
                region_counts[region_id] = region_counts.get(region_id, 0) + 1

        return len(region_counts) == size and all(count == size for count in region_counts.values())

    def apply_region_map(self, region_map: List[List[int]], status_text: str = "Custom regions loaded"):
        """Apply a custom irregular region layout to the current board."""
        if not self._is_valid_region_map(region_map, self.board_size):
            messagebox.showerror(
                "Invalid Regions",
                f"Region map must be a {self.board_size}x{self.board_size} grid with exactly {self.board_size} regions of {self.board_size} cells each."
            )
            return False

        self.region_map = [[int(cell) for cell in row] for row in region_map]
        self.region_shape = None
        self.draw_board()
        self.status_label.config(text=status_text)
        return True

    def _display_value(self, value: int) -> str:
        """Convert a numeric value to a compact label for buttons and cells."""
        if value <= 9:
            return str(value)

        alphabet = string.ascii_uppercase + string.ascii_lowercase
        index = value - 10
        if 0 <= index < len(alphabet):
            return alphabet[index]
        return str(value)

    def rebuild_number_pad(self):
        """Rebuild the number pad for the current board size."""
        if not hasattr(self, 'button_frame'):
            return

        for child in self.button_frame.winfo_children():
            child.destroy()

        columns = 8 if self.board_size > 8 else self.board_size
        columns = max(columns, 1)

        for i in range(1, self.board_size + 1):
            btn = ttk.Button(
                self.button_frame,
                text=self._display_value(i),
                width=3,
                command=lambda n=i: self.input_number(n)
            )
            btn.grid(row=(i - 1) // columns, column=(i - 1) % columns, padx=2, pady=2)

        clear_btn = ttk.Button(
            self.button_frame,
            text="Clear (0)",
            command=lambda: self.input_number(0),
            width=12
        )
        clear_btn.grid(row=(self.board_size // columns) + 1, column=0, columnspan=columns, pady=5)

    def set_custom_dimensions(self):
        """Open a clear modal dialog for custom board and region dimensions."""
        if self.solving:
            messagebox.showwarning("Warning", "Cannot change size while solving!")
            return

        self.ui_input_locked = True
        dialog = tk.Toplevel(self.root)
        dialog.title("Custom Grid Setup")
        dialog.geometry("460x320")
        dialog.configure(bg="#eef2f7")
        dialog.transient(self.root)
        dialog.grab_set()

        def close_dialog():
            self.ui_input_locked = False
            if dialog.winfo_exists():
                dialog.grab_release()
                dialog.destroy()

        def apply_settings():
            try:
                size = int(size_var.get())
                region_rows = int(rows_var.get())
                region_cols = int(cols_var.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter whole numbers for all fields.", parent=dialog)
                return

            if size < 1 or region_rows < 1 or region_cols < 1:
                messagebox.showerror("Invalid Input", "All values must be greater than zero.", parent=dialog)
                return

            if region_rows * region_cols != size:
                messagebox.showerror(
                    "Invalid Dimensions",
                    "For rectangular Sudoku, board size must equal region rows × region cols.",
                    parent=dialog,
                )
                return

            self.region_shape = (region_rows, region_cols)
            self.change_board_size(size)
            self.status_label.config(
                text=f"Custom grid ready: {size}x{size} board with {region_rows}x{region_cols} regions"
            )
            close_dialog()

        title = ttk.Label(dialog, text="Custom Grid Setup", font=("Helvetica", 15, "bold"))
        title.pack(pady=(18, 4))

        info = ttk.Label(
            dialog,
            text=(
                "Enter the board size and the region dimensions.\n"
                "Examples: 8 board with 2x4 regions, or 42 board with 6x7 regions.\n"
                "Rule: board size must equal region rows × region cols."
            ),
            justify="center",
            wraplength=400,
        )
        info.pack(pady=(0, 14))

        form = ttk.Frame(dialog, padding=10)
        form.pack(fill=tk.X)

        size_var = tk.StringVar(value=str(self.board_size))
        rows_var = tk.StringVar(value=str(self.region_shape[0] if self.region_shape else 2))
        cols_var = tk.StringVar(value=str(self.region_shape[1] if self.region_shape else 4))

        entries = [
            ("Board size", size_var),
            ("Region rows", rows_var),
            ("Region cols", cols_var),
        ]

        for row_index, (label_text, variable) in enumerate(entries):
            ttk.Label(form, text=label_text).grid(row=row_index, column=0, sticky="w", padx=(0, 8), pady=6)
            ttk.Entry(form, textvariable=variable, width=18).grid(row=row_index, column=1, sticky="w", pady=6)

        button_row = ttk.Frame(dialog)
        button_row.pack(pady=18)

        ttk.Button(button_row, text="Apply", command=apply_settings).pack(side=tk.LEFT, padx=6)
        ttk.Button(button_row, text="Cancel", command=close_dialog).pack(side=tk.LEFT, padx=6)

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        dialog.wait_window()

    def setup_ui(self):
        """Setup the complete UI"""
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top section - Title and size
        top_section = ttk.Frame(main_container)
        top_section.pack(fill=tk.X, pady=10)
        
        title_label = ttk.Label(
            top_section,
            text="🎮 Complete Sudoku Solver - Any Grid",
            font=("Helvetica", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)

        size_frame = ttk.LabelFrame(top_section, text="Grid Size", padding=5)
        size_frame.pack(side=tk.RIGHT, padx=20)
        
        self.size_var = tk.StringVar(value="9")
        for size in ["1", "4", "9", "16"]:
            ttk.Radiobutton(
                size_frame,
                text=f"{size}x{size}",
                variable=self.size_var,
                value=size,
                command=lambda s=size: self.change_board_size(int(s))
            ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            size_frame,
            text="Custom...",
            command=self.set_custom_dimensions
        ).pack(side=tk.LEFT, padx=8)

        # Main content area
        content = ttk.Frame(main_container)
        content.pack(fill=tk.BOTH, expand=True)

        # Left panel - Canvas and controls
        left_panel = ttk.Frame(content)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas for board
        canvas_frame = ttk.LabelFrame(
            left_panel,
            text="📋 Puzzle Board - Click to select • Keyboard: ↑↓←→ to navigate, 0-9 to input",
            padding=5
        )
        canvas_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.canvas_size,
            height=self.canvas_size,
            bg=self.theme["canvas"],
            cursor='cross'
        )
        self.canvas.pack(padx=5, pady=5)
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.draw_board()

        # Input controls frame
        input_frame = ttk.LabelFrame(left_panel, text="🔢 Quick Input", padding=10)
        input_frame.pack(fill=tk.X, pady=10)
        
        self.button_frame = ttk.Frame(input_frame)
        self.button_frame.pack()
        self.rebuild_number_pad()

        selected_info = ttk.Label(
            input_frame,
            text="Selected: None | Use arrow keys (↑↓←→) and type numbers",
            font=("Helvetica", 9),
            foreground="blue"
        )
        selected_info.pack(pady=5)
        self.selected_info_label = selected_info

        # Right panel - Controls and stats
        right_panel = ttk.Frame(content, width=350)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_panel.pack_propagate(False)

        # Load puzzles
        load_frame = ttk.LabelFrame(right_panel, text="📂 Load Sample", padding=10)
        load_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            load_frame,
            text="Load 9x9 Easy Sample",
            command=lambda: self.load_sample("puzzle_9x9_easy.json")
        ).pack(fill=tk.X, pady=3)
        
        ttk.Button(
            load_frame,
            text="Load 4x4 Easy Sample",
            command=lambda: self.load_sample("puzzle_4x4_easy.json")
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            load_frame,
            text="Load 8x8 2x4 Sample",
            command=lambda: self.load_sample("puzzle_8x8_2x4.json")
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            load_frame,
            text="Load Region Map",
            command=self.load_region_map
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            load_frame,
            text="Reset to Standard Regions",
            command=self.reset_regions
        ).pack(fill=tk.X, pady=3)

        # Main controls
        controls_frame = ttk.LabelFrame(right_panel, text="⚙️ Actions", padding=10)
        controls_frame.pack(fill=tk.X, pady=10)

        self.solve_btn = ttk.Button(
            controls_frame,
            text="🚀 SOLVE",
            command=self.solve_puzzle
        )
        self.solve_btn.pack(fill=tk.X, pady=5)

        ttk.Button(
            controls_frame,
            text="🔄 Reset to Original",
            command=self.reset_puzzle
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            controls_frame,
            text="❌ Clear All",
            command=self.clear_all
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            controls_frame,
            text="💾 Save Puzzle",
            command=self.save_puzzle
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            controls_frame,
            text="📂 Load Puzzle",
            command=self.load_puzzle
        ).pack(fill=tk.X, pady=3)

        # Statistics
        stats_frame = ttk.LabelFrame(right_panel, text="📊 Stats & History", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.stats_text = tk.Text(stats_frame, height=20, width=40, state='disabled', wrap=tk.WORD)
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(
            status_frame,
            text="Ready • Input puzzle clues, then click SOLVE",
            relief='sunken',
            font=("Helvetica", 9)
        )
        self.status_label.pack(fill=tk.X)

        self.update_stats_display()

    def bind_keyboard(self):
        """Bind keyboard controls"""
        self.root.bind_all('<Up>', lambda e: self.move_selection(-1, 0))
        self.root.bind_all('<Down>', lambda e: self.move_selection(1, 0))
        self.root.bind_all('<Left>', lambda e: self.move_selection(0, -1))
        self.root.bind_all('<Right>', lambda e: self.move_selection(0, 1))
        self.root.bind_all('<KeyPress>', self.handle_keypress)
        self.root.bind_all('<Delete>', lambda e: self.input_number(0))
        self.root.bind_all('<BackSpace>', lambda e: self.input_number(0))

    def handle_keypress(self, event):
        """Handle keyboard input from top row keys and numpad."""
        if self.ui_input_locked:
            return 'break'

        key = event.keysym
        char = event.char

        if key in ('Delete', 'BackSpace', 'KP_Delete', 'KP_Decimal'):
            self.input_number(0)
            return 'break'

        if key.startswith('KP_'):
            keypad_value = key[3:]
            if keypad_value.isdigit():
                self.input_number(int(keypad_value))
                return 'break'

        if char.isdigit():
            self.input_number(int(char))
            return 'break'

        if char:
            alphabet = string.ascii_uppercase + string.ascii_lowercase
            if char in alphabet:
                value = 10 + alphabet.index(char)
                if value <= self.board_size:
                    self.input_number(value)
                    return 'break'

        return None

    def move_selection(self, dr: int, dc: int):
        """Move selection with arrow keys"""
        if self.selected_cell is None:
            self.selected_cell = (0, 0)
        else:
            r, c = self.selected_cell
            new_r = (r + dr) % self.board_size
            new_c = (c + dc) % self.board_size
            self.selected_cell = (new_r, new_c)
        
        self.draw_board()
        self.update_selected_display()

    def input_number(self, num: int):
        """Input number at selected cell"""
        if self.solving or self.solved:
            return

        if self.selected_cell is None:
            self.selected_cell = (0, 0)
        
        row, col = self.selected_cell

        self.board[row][col] = num
        self.draw_board()
        self.update_selected_display()
        self.status_label.config(text=f"Entered {num} at ({row+1}, {col+1})")

        if num != 0:
            self.move_to_next_cell(row, col)

    def move_to_next_cell(self, row: int, col: int):
        """Move selection to the next editable cell."""
        for offset in range(1, self.board_size * self.board_size + 1):
            index = (row * self.board_size + col + offset) % (self.board_size * self.board_size)
            next_row = index // self.board_size
            next_col = index % self.board_size
            self.selected_cell = (next_row, next_col)
            self.draw_board()
            self.update_selected_display()
            return

    def change_board_size(self, new_size: int):
        """Change board size"""
        if self.solving:
            messagebox.showwarning("Warning", "Cannot change size while solving!")
            return

        if self.region_shape is not None and self.region_shape[0] * self.region_shape[1] != new_size:
            self.region_shape = None

        self.board_size = new_size
        self.board = [[0] * new_size for _ in range(new_size)]
        self.original_board = [[0] * new_size for _ in range(new_size)]
        self.region_map = self._create_standard_region_map(new_size)
        self.cell_size = self.canvas_size // new_size
        self.selected_cell = None
        self.solved = False
        self.solution = []
        self.rebuild_number_pad()
        
        self.canvas.delete('all')
        self.draw_board()
        self.update_stats_display()
        self.status_label.config(text=f"Size changed to {new_size}x{new_size}")

    def draw_board(self):
        """Draw the sudoku board"""
        self.canvas.delete('all')

        # Draw a subtle board background first.
        self.canvas.create_rectangle(0, 0, self.canvas_size, self.canvas_size, fill="#f9fbff", outline="")
        
        # Draw cells
        for i in range(self.board_size):
            for j in range(self.board_size):
                x1 = j * self.cell_size
                y1 = i * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                # Selected cell
                if self.selected_cell == (i, j):
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='lightblue', outline='')
                # Original puzzle clues (only if unchanged from the loaded/captured puzzle)
                elif self.board[i][j] != 0 and self.original_board[i][j] != 0 and self.board[i][j] == self.original_board[i][j]:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='lightyellow', outline='')
                # User entered or edited cell
                elif self.board[i][j] != 0:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='lightgreen', outline='')
                
                # Draw numbers
                if self.board[i][j] != 0:
                    if self.original_board[i][j] != 0 and self.board[i][j] == self.original_board[i][j]:
                        color = 'darkgreen'  # Original clue
                    else:
                        color = 'darkblue'  # User input
                    
                    num_text = self._display_value(self.board[i][j])
                    
                    x = j * self.cell_size + self.cell_size // 2
                    y = i * self.cell_size + self.cell_size // 2
                    
                    self.canvas.create_text(
                        x, y,
                        text=num_text,
                        font=("Arial", max(12, self.cell_size // 3), "bold"),
                        fill=color
                    )

        # Draw grid last so the lines stay visible over filled cells.
        for i in range(self.board_size + 1):
            x = i * self.cell_size
            self.canvas.create_line(x, 0, x, self.canvas_size, width=1, fill="#c5ced8")
            self.canvas.create_line(0, x, self.canvas_size, x, width=1, fill="#c5ced8")

        # Highlight irregular region boundaries.
        boundary_color = "#1f4b99"
        for row in range(self.board_size):
            for col in range(self.board_size):
                region_id = self.region_map[row][col]
                x1 = col * self.cell_size
                y1 = row * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                if row == 0 or self.region_map[row - 1][col] != region_id:
                    self.canvas.create_line(x1, y1, x2, y1, width=3, fill=boundary_color)
                if col == 0 or self.region_map[row][col - 1] != region_id:
                    self.canvas.create_line(x1, y1, x1, y2, width=3, fill=boundary_color)
                if row == self.board_size - 1 or self.region_map[row + 1][col] != region_id:
                    self.canvas.create_line(x1, y2, x2, y2, width=3, fill=boundary_color)
                if col == self.board_size - 1 or self.region_map[row][col + 1] != region_id:
                    self.canvas.create_line(x2, y1, x2, y2, width=3, fill=boundary_color)

    def on_canvas_click(self, event):
        """Handle canvas click"""
        col = event.x // self.cell_size
        row = event.y // self.cell_size
        
        if 0 <= row < self.board_size and 0 <= col < self.board_size:
            self.selected_cell = (row, col)
            self.draw_board()
            self.update_selected_display()

    def update_selected_display(self):
        """Update selected cell display"""
        if self.selected_cell:
            r, c = self.selected_cell
            value = self.board[r][c] if self.board[r][c] != 0 else "empty"
            is_clue = self.original_board[r][c] != 0
            self.selected_info_label.config(
                text=f"Selected: ({r+1}, {c+1}) = {value} {'[CLUE]' if is_clue else ''}"
            )
        else:
            self.selected_info_label.config(text="Selected: None")

    def solve_puzzle(self):
        """Solve the current puzzle"""
        if self.solving:
            messagebox.showwarning("Warning", "Already solving!")
            return
        
        if self.solved:
            messagebox.showinfo("Info", "Puzzle already solved! Click 'Clear All' or 'Reset' to start over.")
            return
        
        self.user_verified_correct = False
        self.original_board = [row[:] for row in self.board]

        # Keep the current editable grid as the puzzle source.
        self.solving = True
        self.solve_btn.config(state='disabled', text="⏳ Solving...")
        self.status_label.config(text="Solving puzzle...")
        self.root.update()
        
        thread = threading.Thread(target=self._solve_thread)
        thread.daemon = True
        thread.start()

    def _solve_thread(self):
        """Solve in background thread"""
        try:
            puzzle_board = [row[:] for row in self.original_board]
            self.solver = SudokuSolver(
                puzzle_board,
                self.board_size,
                region_map=self.region_map,
                region_shape=self.region_shape,
            )
            
            if self.solver.solve():
                self.solution = self.solver.get_solution()
                self.board = [row[:] for row in self.solution]
                self.solved = True
                
                # Ask for verification
                self.root.after(0, self._ask_solution_verification)
                
                # Record solve
                stats = self.solver.get_stats()
                self.learner.record_solve(
                    self.board_size,
                    stats['time'],
                    stats['moves'],
                    hashlib.md5(str(self.original_board).encode()).hexdigest()
                )
            else:
                self.root.after(0, lambda: messagebox.showerror("No Solution", "This puzzle has no solution!"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Solving error: {str(e)}"))
        finally:
            self.solving = False
            self.root.after(0, self._update_ui_after_solve)

    def _ask_solution_verification(self):
        """Ask user if solution is correct"""
        result = messagebox.askyesno(
            "Solution Verification",
            "✓ Puzzle solved!\n\nWas this solution correct?\n(This helps improve the solver)"
        )
        self.user_verified_correct = result
        self.learner.record_solution_accuracy(result)

    def _update_ui_after_solve(self):
        """Update UI after solving"""
        self.solve_btn.config(state='normal', text="🚀 SOLVE")
        self.draw_board()
        
        if self.solved:
            accuracy = "✓ Correct" if self.user_verified_correct else "✗ Needs checking"
            self.status_label.config(
                text=f"Solved! {accuracy} • Review solution above"
            )
        else:
            self.status_label.config(text="Could not solve - puzzle may be invalid")
        
        self.update_stats_display()

    def reset_puzzle(self):
        """Reset to original puzzle"""
        self.board = [row[:] for row in self.original_board]
        self.solved = False
        self.solution = []
        self.draw_board()
        self.status_label.config(text="Reset to original puzzle")

    def reset_regions(self):
        """Reset to the standard square Sudoku regions for the current board size."""
        if self.region_shape is None and int(self.board_size ** 0.5) ** 2 != self.board_size:
            messagebox.showinfo(
                "Info",
                "This board size does not have a square standard layout. Load a region map or use Custom..."
            )
            return

        self.region_map = self._create_standard_region_map(self.board_size)
        self.draw_board()
        self.status_label.config(text="Reset to standard regions")

    def load_region_map(self):
        """Load a region layout from a JSON file."""
        file_path = filedialog.askopenfilename(
            defaultdir=self.samples_dir,
            filetypes=[("JSON files", "*.json")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            region_map = data.get('regions', data)
            if self.apply_region_map(region_map, f"Region map loaded: {Path(file_path).name}"):
                messagebox.showinfo("Success", "Region map loaded!")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load region map: {exc}")

    def clear_all(self):
        """Clear entire board"""
        if messagebox.askyesno("Confirm", "Clear the entire board?"):
            self.board = [[0] * self.board_size for _ in range(self.board_size)]
            self.original_board = [[0] * self.board_size for _ in range(self.board_size)]
            self.solved = False
            self.solution = []
            self.selected_cell = None
            self.draw_board()
            self.status_label.config(text="Board cleared - Ready for new puzzle")

    def save_puzzle(self):
        """Save puzzle to file"""
        file_path = filedialog.asksaveasfilename(
            defaultdir=self.samples_dir,
            filetypes=[("JSON files", "*.json")],
            initialfile=f"puzzle_{self.board_size}x{self.board_size}.json"
        )
        
        if file_path:
            data = {
                'size': self.board_size,
                'puzzle': self.original_board,
                'regions': self.region_map,
                'region_shape': self.region_shape,
                'solution': self.solution if self.solution else None
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Success", f"Puzzle saved to {file_path}")
            self.status_label.config(text="Puzzle saved")

    def load_puzzle(self):
        """Load puzzle from file"""
        file_path = filedialog.askopenfilename(
            defaultdir=self.samples_dir,
            filetypes=[("JSON files", "*.json")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                new_size = data.get('size', 9)
                if data.get('region_shape'):
                    self.region_shape = tuple(data['region_shape'])
                if new_size != self.board_size:
                    self.change_board_size(new_size)
                
                self.original_board = data['puzzle']
                self.board = [row[:] for row in self.original_board]
                if 'regions' in data:
                    if not self.apply_region_map(data['regions'], f"Puzzle loaded: {Path(file_path).name}"):
                        return
                if data.get('region_shape'):
                    self.region_shape = tuple(data['region_shape'])
                self.solution = data.get('solution', [])
                self.solved = False
                
                self.draw_board()
                self.status_label.config(text=f"Puzzle loaded: {Path(file_path).name}")
                messagebox.showinfo("Success", "Puzzle loaded!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def load_sample(self, filename: str):
        """Load sample puzzle"""
        sample_path = self.samples_dir / filename
        
        if not sample_path.exists():
            messagebox.showerror("Error", f"Sample not found: {filename}")
            return
        
        try:
            with open(sample_path, 'r') as f:
                data = json.load(f)
            
            new_size = data.get('size', 9)
            if data.get('region_shape'):
                self.region_shape = tuple(data['region_shape'])
            if new_size != self.board_size:
                self.change_board_size(new_size)
            
            self.original_board = data['puzzle']
            self.board = [row[:] for row in self.original_board]
            if 'regions' in data:
                if not self.apply_region_map(data['regions'], f"Sample loaded: {filename}"):
                    return
            if data.get('region_shape'):
                self.region_shape = tuple(data['region_shape'])
            self.solution = []
            self.solved = False
            
            self.draw_board()
            self.status_label.config(text=f"Sample loaded: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sample: {str(e)}")

    def update_stats_display(self):
        """Update statistics display"""
        stats = self.learner.get_stats()
        
        self.stats_text.config(state='normal')
        self.stats_text.delete(1.0, tk.END)
        
        display_text = f"""
{'='*35}
SOLVER STATISTICS
{'='*35}

📊 Overall Performance:
   Total Solved: {stats.get('total_solved', 0)}
   Accuracy: {stats.get('accuracy_percentage', 0):.1f}%
   Confidence: {stats.get('confidence_score', 0):.1f}%

⏱️  Speed Statistics:
   Avg Time: {stats.get('avg_time', 0):.4f}s
   Fastest: {stats.get('fastest_time', 0):.6f}s
   Slowest: {stats.get('slowest_time', 0):.6f}s

📈 By Grid Size:
"""
        
        for size, size_stats in stats.get('by_size', {}).items():
            display_text += f"\n   {size}x{size}:"
            display_text += f"\n      Solves: {size_stats.get('count', 0)}"
            display_text += f"\n      Accuracy: {size_stats.get('accuracy', 0):.1f}%"
            display_text += f"\n      Avg: {size_stats.get('avg_time', 0):.4f}s"
        
        display_text += f"\n\n{'='*35}\nVERIFICATION STATUS\n{'='*35}\n"
        display_text += f"Verified Correct: {stats.get('verified_correct', 0)}\n"
        display_text += f"Needs Review: {stats.get('needs_review', 0)}\n"
        
        self.stats_text.insert(1.0, display_text)
        self.stats_text.config(state='disabled')

    def _locked_cells(self):
        """Get set of locked (original) cells"""
        return {(i, j) for i in range(self.board_size) for j in range(self.board_size) if self.original_board[i][j] != 0}

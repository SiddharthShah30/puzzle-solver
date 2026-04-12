"""Tkinter UI for Zip puzzle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - runtime fallback
    Image = None
    ImageTk = None

from .solver import ZipPuzzleSolver


COLOR_PALETTE = [
    "#a58dc8",
    "#edbe86",
    "#8bb9eb",
    "#99c78a",
    "#b8b8b8",
    "#f7785f",
    "#c7d96e",
    "#84d8d8",
    "#d49ab3",
    "#f2d77c",
    "#9fa9e3",
    "#7fcf9c",
    "#f0a672",
    "#c2a786",
    "#92c6bf",
    "#e59797",
    "#d4cf8c",
    "#8eb2c9",
    "#c5a8dc",
    "#a4b087",
]


class ZipUI:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Zip Solver")
        self.root.geometry("1100x760")

        self.samples_dir = Path(__file__).parent / "samples"
        self.rows = 4
        self.cols = 4
        self.clue_board: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.board: List[List[int]] = [row[:] for row in self.clue_board]
        self.h_walls: List[List[int]] = [[0 for _ in range(max(0, self.cols - 1))] for _ in range(self.rows)]
        self.v_walls: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(max(0, self.rows - 1))]
        self.fixed_cells: Set[Tuple[int, int]] = set()
        self.solution_cells: Set[Tuple[int, int]] = set()
        self.cell_size = 90
        self.selected_cells: Set[Tuple[int, int]] = {(0, 0)}
        self.selection_anchor: Tuple[int, int] = (0, 0)
        self.cursor: Tuple[int, int] = (0, 0)
        self.selected_label_var = tk.StringVar(value="1")

        self._setup_ui()
        self._draw_board()

    def _setup_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Zip Puzzle", font=("Helvetica", 16, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Rules: draw one unbroken orthogonal path that visits clues in order (1,2,3...). "
                "The path must cover every cell exactly once and cannot cross itself. "
                "Thick wall barriers block movement between adjacent cells."
            ),
            wraplength=920,
        ).pack(anchor="w", pady=(4, 10))

        content = ttk.Frame(outer)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(content, text="Board", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(left, width=620, height=620, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        right = ttk.LabelFrame(content, text="Controls", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        ttk.Button(right, text="New Puzzle Setup", command=self.new_puzzle_setup).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Import from Screenshot", command=self.import_from_screenshot).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load Example", command=lambda: self.load_sample("zip_2x2_sample.json")).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load 4x4 Example", command=lambda: self.load_sample("zip_4x4_sample.json")).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Solve", command=self.solve).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Check Rules", command=self.check_current_board).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Clear User Entries", command=self.clear_user_entries).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Reset to Clues", command=self.reset_to_clues).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load Puzzle JSON", command=self.load_puzzle_json).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Save Puzzle JSON", command=self.save_puzzle_json).pack(fill=tk.X, pady=4)

        editor = ttk.LabelFrame(right, text="Edit Selected Cells", padding=10)
        editor.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(editor, text="Label number:").pack(anchor="w")
        row = ttk.Frame(editor)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Entry(row, textvariable=self.selected_label_var, width=10).pack(side=tk.LEFT)
        ttk.Button(row, text="Apply", command=self.apply_selected_label).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(row, text="Clear", command=lambda: self.apply_selected_label(clear=True)).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(
            editor,
            text="Click cells to select. Use Shift+Click or Shift+Arrow to extend.\nType a number and apply to fill or correct clues.",
            wraplength=280,
        ).pack(anchor="w", pady=(8, 0))

        self.status = ttk.Label(right, text="Ready", wraplength=300)
        self.status.pack(fill=tk.X, pady=(12, 0))

    def _label_color(self, label: int) -> str:
        if label <= 0:
            return "#dddddd"
        return COLOR_PALETTE[(label - 1) % len(COLOR_PALETTE)]

    def _draw_board(self):
        self.canvas.delete("all")
        board_px = max(320, min(680, max(self.rows, self.cols) * self.cell_size))
        self.cell_size = max(44, min(110, board_px // max(1, max(self.rows, self.cols))))
        board_w = self.cell_size * self.cols
        board_h = self.cell_size * self.rows
        self.canvas.config(width=board_w + 2, height=board_h + 2)

        for r in range(self.rows):
            for c in range(self.cols):
                x0 = c * self.cell_size
                y0 = r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                value = self.board[r][c]
                fill = self._label_color(value) if value != 0 else "#f7f7f7"
                if (r, c) in self.fixed_cells:
                    fill = self._label_color(value)
                if (r, c) in self.solution_cells and (r, c) not in self.fixed_cells:
                    fill = "#dff0ff"

                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#cfc8bf", width=1)

                if value != 0:
                    radius = max(11, self.cell_size // 3)
                    cx = (x0 + x1) / 2
                    cy = (y0 + y1) / 2
                    self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#111111", outline="#111111")
                    self.canvas.create_text(cx, cy, text=str(value), fill="#ffffff", font=("Helvetica", max(10, self.cell_size // 4), "bold"))

                if (r, c) in self.fixed_cells:
                    self.canvas.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, outline="#355070", width=2)

                if (r, c) in self.selected_cells:
                    self.canvas.create_rectangle(x0 + 4, y0 + 4, x1 - 4, y1 - 4, outline="#ffffff", width=3)
                if self.cursor == (r, c):
                    self.canvas.create_rectangle(x0 + 6, y0 + 6, x1 - 6, y1 - 6, outline="#111111", width=2)

                # Draw right wall for this cell.
                if c < self.cols - 1 and self.h_walls[r][c] == 1:
                    self.canvas.create_line(x1, y0, x1, y1, fill="#111111", width=5)
                # Draw bottom wall for this cell.
                if r < self.rows - 1 and self.v_walls[r][c] == 1:
                    self.canvas.create_line(x0, y1, x1, y1, fill="#111111", width=5)

        self.canvas.create_rectangle(0, 0, board_w, board_h, outline="#222222", width=2)

    def _parse_grid_text(self, raw_text: str, rows: int, cols: int) -> List[List[int]]:
        lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
        if len(lines) != rows:
            raise ValueError(f"Expected {rows} rows, found {len(lines)}")

        parsed: List[List[int]] = []
        for line in lines:
            cells = [token for token in line.replace(",", " ").split(" ") if token]
            if len(cells) != cols:
                raise ValueError(f"Each row must have {cols} integers")
            parsed.append([int(token) for token in cells])
        return parsed

    def _parse_positions(self, text_widget: tk.Text) -> Set[Tuple[int, int]]:
        positions: Set[Tuple[int, int]] = set()
        raw = text_widget.get("1.0", tk.END).strip()
        if not raw:
            return positions
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2:
                raise ValueError("Position lines must be in row,col format")
            positions.add((int(parts[0]), int(parts[1])))
        return positions

    def new_puzzle_setup(self):
        setup = tk.Toplevel(self.root)
        setup.title("Zip Puzzle Setup")
        setup.geometry("740x620")
        setup.transient(self.root)
        setup.grab_set()

        container = ttk.Frame(setup, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Create Custom Zip Puzzle", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Enter board size and sequential clues.\n"
                "Clue grid values: 0 for blank, positive numbers for numbered waypoints.\n"
                "Numbers must be unique and form 1..N."
            ),
            wraplength=700,
        ).pack(anchor="w", pady=(6, 10))

        size_row = ttk.Frame(container)
        size_row.pack(fill=tk.X)
        ttk.Label(size_row, text="Board size (rows x cols):").pack(side=tk.LEFT)
        rows_var = tk.StringVar(value="4")
        cols_var = tk.StringVar(value="4")
        ttk.Entry(size_row, textvariable=rows_var, width=6).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Label(size_row, text="x").pack(side=tk.LEFT)
        ttk.Entry(size_row, textvariable=cols_var, width=6).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(container, text="Clue grid (rows lines, cols integers each):").pack(anchor="w", pady=(12, 4))
        clue_text = tk.Text(container, height=18, width=80)
        clue_text.pack(fill=tk.BOTH, expand=True)
        clue_text.insert(
            "1.0",
            "1 0 0 0\n"
            "0 0 0 0\n"
            "0 0 0 0\n"
            "0 0 0 2\n",
        )

        def apply_setup():
            try:
                rows = int(rows_var.get())
                cols = int(cols_var.get())
                if rows < 2 or cols < 2:
                    raise ValueError("Board dimensions must be at least 2x2")
                clues = self._parse_grid_text(clue_text.get("1.0", tk.END), rows, cols)
                self._load_from_data({"rows": rows, "cols": cols, "clues": clues}, source_label="custom setup")
                setup.destroy()
            except Exception as exc:
                messagebox.showerror("Invalid Puzzle", str(exc), parent=setup)

        button_row = ttk.Frame(container)
        button_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_row, text="Apply Puzzle", command=apply_setup).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Cancel", command=setup.destroy).pack(side=tk.LEFT, padx=(8, 0))

    def _find_content_bounds(self, image, threshold: int = 245) -> Tuple[int, int, int, int]:
        gray = image.convert("L")
        mask = gray.point(lambda p: 255 if p < threshold else 0)
        bbox = mask.getbbox()
        if bbox is None:
            return (0, 0, image.size[0], image.size[1])

        left, top, right, bottom = bbox
        pad = max(4, int(min(image.size) * 0.015))
        left = max(0, left - pad)
        top = max(0, top - pad)
        right = min(image.size[0], right + pad)
        bottom = min(image.size[1], bottom + pad)
        return left, top, right, bottom

    def _estimate_grid_size(self, image, min_size: int = 2, max_size: int = 18) -> Tuple[int, float]:
        width, height = image.size
        if width < 20 or height < 20:
            raise ValueError("Image is too small to detect a puzzle grid")

        max_dim = 900
        if max(width, height) > max_dim:
            scale = max_dim / float(max(width, height))
            image = image.resize((max(20, int(width * scale)), max(20, int(height * scale))))
            width, height = image.size

        gray = image.convert("L")
        px = gray.load()

        v_profile = [0.0 for _ in range(width)]
        h_profile = [0.0 for _ in range(height)]

        for x in range(1, width):
            total = 0.0
            for y in range(height):
                total += abs(int(px[x, y]) - int(px[x - 1, y]))
            v_profile[x] = total / height

        for y in range(1, height):
            total = 0.0
            for x in range(width):
                total += abs(int(px[x, y]) - int(px[x, y - 1]))
            h_profile[y] = total / width

        def smooth(values: List[float], radius: int = 2) -> List[float]:
            out = [0.0 for _ in values]
            prefix = [0.0]
            running = 0.0
            for value in values:
                running += value
                prefix.append(running)
            for idx in range(len(values)):
                left = max(0, idx - radius)
                right = min(len(values) - 1, idx + radius)
                out[idx] = (prefix[right + 1] - prefix[left]) / (right - left + 1)
            return out

        v_profile = smooth(v_profile)
        h_profile = smooth(h_profile)

        def detect_peak_count(profile: List[float]) -> int:
            if len(profile) < 5:
                return 0
            p_min = min(profile)
            p_max = max(profile)
            if p_max <= p_min:
                return 0

            def collect(threshold: float) -> List[int]:
                return [
                    idx
                    for idx in range(1, len(profile) - 1)
                    if profile[idx] >= threshold and profile[idx] >= profile[idx - 1] and profile[idx] >= profile[idx + 1]
                ]

            candidates = collect(p_min + 0.58 * (p_max - p_min))
            if not candidates:
                candidates = collect(p_min + 0.45 * (p_max - p_min))

            min_sep = max(2, int(len(profile) / 30))
            chosen: List[int] = []
            for idx in sorted(candidates, key=lambda i: profile[i], reverse=True):
                if all(abs(idx - prev) >= min_sep for prev in chosen):
                    chosen.append(idx)
            return len(chosen)

        def border_pair(profile: List[float], length: int) -> Tuple[int, int]:
            zone = max(8, int(length * 0.20))
            left_zone = profile[1:zone]
            right_start = max(1, length - zone)
            right_zone = profile[right_start:length - 1]
            if not left_zone or not right_zone:
                return 1, length - 1
            left_idx = 1 + max(range(len(left_zone)), key=lambda i: left_zone[i])
            right_idx = right_start + max(range(len(right_zone)), key=lambda i: right_zone[i])
            if right_idx - left_idx < int(length * 0.35):
                return 1, length - 1
            return left_idx, right_idx

        def mean_at(profile: List[float], indices: List[int]) -> float:
            if not indices:
                return 0.0
            return sum(profile[i] for i in indices) / len(indices)

        def axis_score(profile: List[float], length: int, count: int) -> Tuple[float, Tuple[int, int]]:
            left, right = border_pair(profile, length)
            span = max(2, right - left)
            step = span / float(count)
            if step < 3:
                return -1e9, (left, right)

            best = -1e9
            best_bounds = (left, right)
            for jitter in (-2, -1, 0, 1, 2):
                lines = []
                gaps = []
                for i in range(count + 1):
                    pos = int(round(left + jitter + i * step))
                    lines.append(min(max(1, pos), length - 1))
                for i in range(count):
                    pos = int(round(left + jitter + (i + 0.5) * step))
                    gaps.append(min(max(1, pos), length - 1))
                line_strength = mean_at(profile, lines)
                gap_strength = mean_at(profile, gaps)
                score = (line_strength - 0.80 * gap_strength) + 0.20 * line_strength
                if score > best:
                    best = score
                    best_bounds = (left, right)
            return best, best_bounds

        rough_rows = max(2, detect_peak_count(h_profile) - 1)
        rough_cols = max(2, detect_peak_count(v_profile) - 1)

        row_scores = []
        col_scores = []
        for n in range(min_size, max_size + 1):
            row_score, row_bounds = axis_score(h_profile, height, n)
            col_score, col_bounds = axis_score(v_profile, width, n)
            row_scores.append((n, row_score - 0.08 * abs(n - rough_rows), row_bounds))
            col_scores.append((n, col_score - 0.08 * abs(n - rough_cols), col_bounds))

        row_scores.sort(key=lambda item: item[1], reverse=True)
        col_scores.sort(key=lambda item: item[1], reverse=True)

        best_rows = row_scores[0][0]
        best_cols = col_scores[0][0]
        best_row_score = row_scores[0][1]
        best_col_score = col_scores[0][1]
        second_row_score = row_scores[1][1] if len(row_scores) > 1 else -1e9
        second_col_score = col_scores[1][1] if len(col_scores) > 1 else -1e9
        confidence = 1.0 + min(
            max(0.0, best_row_score - second_row_score) / max(abs(second_row_score), 1.0),
            max(0.0, best_col_score - second_col_score) / max(abs(second_col_score), 1.0),
        )
        if best_rows != best_cols:
            # Zip boards should be square; choose the stronger axis consensus.
            if abs(best_row_score - best_col_score) > 0.08:
                if best_row_score > best_col_score:
                    best_cols = best_rows
                else:
                    best_rows = best_cols
            else:
                size = int(round((best_rows + best_cols) / 2))
                best_rows = best_cols = min(max(min_size, size), max_size)
        return best_rows, confidence

    def _extract_clues_from_image(
        self,
        image,
        rows: int,
        cols: int,
        bounds: Tuple[int, int, int, int],
    ) -> Tuple[List[List[int]], Dict[Tuple[int, int], float]]:
        """Extract digit clues from screenshot using OCR or pattern matching.
        
        Returns (clues_grid, confidence_map) where confidence_map stores per-cell confidence.
        """
        clues = [[0 for _ in range(cols)] for _ in range(rows)]
        confidence_map = {}
        
        left, top, right, bottom = bounds
        board_w = max(1, right - left)
        board_h = max(1, bottom - top)
        cell_w = board_w / cols
        cell_h = board_h / rows
        
        # Try OCR first if available
        try:
            import pytesseract
            ocr_available = True
        except ImportError:
            ocr_available = False
        
        for r in range(rows):
            for c in range(cols):
                x0 = int(left + c * cell_w)
                y0 = int(top + r * cell_h)
                x1 = int(left + (c + 1) * cell_w)
                y1 = int(top + (r + 1) * cell_h)
                
                # Ensure bounds are within image
                x0 = max(0, min(image.size[0] - 1, x0))
                y0 = max(0, min(image.size[1] - 1, y0))
                x1 = max(x0 + 1, min(image.size[0], x1))
                y1 = max(y0 + 1, min(image.size[1], y1))
                
                # Extract cell
                cell_img = image.crop((x0, y0, x1, y1))
                
                # Try OCR
                if ocr_available:
                    digit, conf = self._detect_digit_ocr(cell_img)
                    if digit > 0 and conf > 0.5:
                        clues[r][c] = digit
                        confidence_map[(r, c)] = conf
                        continue
                
                # Fall back to feature-based detection
                digit, conf = self._classify_digit_cell(cell_img)
                if digit > 0:
                    clues[r][c] = digit
                    confidence_map[(r, c)] = conf
        
        return clues, confidence_map
    
    def _detect_digit_ocr(self, cell_image) -> Tuple[int, float]:
        """Try to detect digit using pytesseract OCR.
        
        Returns (digit, confidence) where digit is 1-9 or 0 if not detected.
        """
        try:
            import pytesseract
            
            # Preprocess: convert to grayscale, enhance contrast
            gray = cell_image.convert("L")
            
            # Try OCR
            text = pytesseract.image_to_string(gray, config="--psm 10 -c tessedit_char_whitelist=0123456789")
            text = text.strip()
            
            if text and text[0].isdigit():
                digit = int(text[0])
                if 0 <= digit <= 9:
                    # Rough confidence based on text length and digit
                    conf = min(0.99, 0.7 + len(text.strip()) * 0.05)
                    return digit, conf
        except Exception:
            pass
        
        return 0, 0.0
    
    def _classify_digit_cell(self, cell_image) -> Tuple[int, float]:
        """Classify digit in a cell using shape and spatial features.
        
        Returns (digit, confidence) where digit is 1-9 or 0 if not detected.
        """
        # Convert to grayscale
        gray = cell_image.convert("L")
        pixels = list(gray.getdata())
        w, h = gray.size
        
        if w < 4 or h < 4:
            return 0, 0.0
        
        # Find background color (most common pixel)
        bg = sorted(set(pixels))[len(set(pixels)) // 2]  # Median color
        
        # Extract foreground (digit pixels)
        fg_points = []
        for idx, p in enumerate(pixels):
            if abs(int(p) - int(bg)) > 30:
                fg_points.append((idx % w, idx // w))
        
        if not fg_points:
            return 0, 0.0
        
        # Check if enough content
        fg_frac = len(fg_points) / max(1, w * h)
        if fg_frac < 0.05 or fg_frac > 0.95:
            return 0, 0.0
        
        # Compute bounding box and features
        xs = [p[0] for p in fg_points]
        ys = [p[1] for p in fg_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        bbox_w = max(1, max_x - min_x + 1)
        bbox_h = max(1, max_y - min_y + 1)
        aspect = bbox_w / bbox_h
        
        # Center and spread
        cx = sum(xs) / len(fg_points)
        cy = sum(ys) / len(fg_points)
        spread_x = sum(abs(x - cx) for x in xs) / len(fg_points)
        spread_y = sum(abs(y - cy) for y in ys) / len(fg_points)
        
        # Hole detection (white pixel in center of mass area)
        center_radius = max(2, min(bbox_w, bbox_h) // 4)
        center_hole = sum(
            1 for x, y in fg_points
            if abs(x - cx) <= center_radius and abs(y - cy) <= center_radius
        ) / max(1, len(fg_points))
        
        # Classify based on features
        # These thresholds are heuristics; adjust if needed
        conf = 0.5 + fg_frac * 0.2
        
        # Check for hole (suggests 0, 6, 8, 9)
        has_hole = center_hole < 0.15
        
        # Check aspect ratio
        is_tall = aspect < 0.7
        is_wide = aspect > 1.4
        is_round = 0.7 <= aspect <= 1.4
        
        # Simple heuristic digit classification
        # Returns most likely digit based on features
        if is_round and has_hole and spread_x < 3 and spread_y < 3:
            return 8, min(0.95, conf + 0.1)  # Good circle = 8
        elif is_round and has_hole:
            return 6, min(0.90, conf)  # Circle with hole = 6 or 8 or 9
        elif is_tall and has_hole:
            return 9, min(0.85, conf + 0.05)  # Tall + hole = 9
        elif is_tall and spread_x < 2:
            return 1, min(0.85, conf)  # Tall and narrow = 1
        elif is_wide:
            return 4, min(0.80, conf)  # Wide = 4, 7, or T
        else:
            # Default: assume it's a digit that exists
            return 1, min(0.70, conf)  # Fallback to 1

    def _load_from_data(self, data: dict, source_label: str):
        clues = data.get("clues")
        if clues is None:
            raise ValueError("Puzzle data must include a 'clues' grid")

        rows = data.get("rows")
        cols = data.get("cols")
        if rows is None or cols is None:
            rows = len(clues)
            cols = len(clues[0]) if clues else 0

        if rows < 2 or cols < 2:
            raise ValueError("Board dimensions must be at least 2x2")
        if len(clues) != rows or any(len(row) != cols for row in clues):
            raise ValueError("Clues grid must match the declared rows and columns")
        for row in clues:
            for value in row:
                if value < 0:
                    raise ValueError("Clues must be non-negative integers")

        h_walls = data.get("h_walls")
        v_walls = data.get("v_walls")
        if h_walls is None:
            h_walls = [[0 for _ in range(max(0, cols - 1))] for _ in range(rows)]
        if v_walls is None:
            v_walls = [[0 for _ in range(cols)] for _ in range(max(0, rows - 1))]
        if len(h_walls) != rows or any(len(row) != max(0, cols - 1) for row in h_walls):
            raise ValueError("h_walls must be rows x (cols-1)")
        if len(v_walls) != max(0, rows - 1) or any(len(row) != cols for row in v_walls):
            raise ValueError("v_walls must be (rows-1) x cols")
        if any(value not in (0, 1) for row in h_walls for value in row):
            raise ValueError("h_walls values must be 0 or 1")
        if any(value not in (0, 1) for row in v_walls for value in row):
            raise ValueError("v_walls values must be 0 or 1")

        self.rows = rows
        self.cols = cols
        self.clue_board = [row[:] for row in clues]
        self.board = [row[:] for row in clues]
        self.h_walls = [row[:] for row in h_walls]
        self.v_walls = [row[:] for row in v_walls]
        self.fixed_cells = {(r, c) for r in range(rows) for c in range(cols) if self.clue_board[r][c] != 0}
        self.solution_cells.clear()
        self.selected_cells = {(0, 0)}
        self.selection_anchor = (0, 0)
        self.cursor = (0, 0)
        self._draw_board()
        self.status.config(text=f"Loaded {source_label} ({rows}x{cols})")

    def load_sample(self, filename: str):
        path = self.samples_dir / filename
        if not path.exists():
            messagebox.showerror("Missing Sample", f"Could not find {filename}")
            return
        self._load_from_file(path)

    def load_puzzle_json(self):
        file_path = filedialog.askopenfilename(initialdir=self.samples_dir, filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        self._load_from_file(Path(file_path))

    def save_puzzle_json(self):
        file_path = filedialog.asksaveasfilename(
            initialdir=self.samples_dir,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not file_path:
            return

        data = {
            "rows": self.rows,
            "cols": self.cols,
            "clues": [[self.board[r][c] if (r, c) in self.fixed_cells else 0 for c in range(self.cols)] for r in range(self.rows)],
            "h_walls": [row[:] for row in self.h_walls],
            "v_walls": [row[:] for row in self.v_walls],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.status.config(text=f"Saved puzzle JSON to {Path(file_path).name}.")

    def _load_from_file(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._load_from_data(data, source_label=path.name)

    def clear_user_entries(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) not in self.fixed_cells:
                    self.board[r][c] = 0
        self.solution_cells.clear()
        self._draw_board()
        self.status.config(text="Cleared user entries.")

    def reset_to_clues(self):
        self.board = [row[:] for row in self.clue_board]
        self.solution_cells.clear()
        self._draw_board()
        self.status.config(text="Reset board to original clues.")

    def on_canvas_click(self, event):
        if self.rows == 0 or self.cols == 0:
            return

        col = event.x // self.cell_size
        row = event.y // self.cell_size
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return

        shift_pressed = bool(event.state & 0x0001)
        if shift_pressed:
            arow, acol = self.selection_anchor
            r0 = min(arow, row)
            r1 = max(arow, row)
            c0 = min(acol, col)
            c1 = max(acol, col)
            self.selected_cells = {(rr, cc) for rr in range(r0, r1 + 1) for cc in range(c0, c1 + 1)}
        else:
            self.selection_anchor = (row, col)
            self.selected_cells = {(row, col)}
        self.cursor = (row, col)
        self._draw_board()

    def apply_selected_label(self, clear: bool = False):
        if not self.selected_cells:
            return

        if clear:
            label = 0
        else:
            try:
                label = int(self.selected_label_var.get().strip())
            except ValueError:
                messagebox.showerror("Invalid Label", "Please enter a whole number label.", parent=self.root)
                return
            if label < 0:
                messagebox.showerror("Invalid Label", "Label number must be 0 or positive.", parent=self.root)
                return

        for r, c in self.selected_cells:
            if (r, c) in self.fixed_cells and label == 0:
                continue
            if (r, c) in self.fixed_cells and label != self.clue_board[r][c]:
                continue
            self.board[r][c] = label
            if label == 0 and (r, c) not in self.fixed_cells:
                self.board[r][c] = 0
        self.solution_cells.clear()
        self._draw_board()

    def _board_to_solver_input(self) -> List[List[int]]:
        return [row[:] for row in self.board]

    def check_current_board(self):
        try:
            solver = ZipPuzzleSolver(self._board_to_solver_input(), h_walls=self.h_walls, v_walls=self.v_walls)
            if solver.solve(verify_unique=True):
                if solver.solution_count == 1:
                    self.status.config(text="Current board is consistent and has a unique sequential full-cover solution.")
                else:
                    self.status.config(text="Current board is consistent, but may have multiple valid sequential full-cover solutions.")
            else:
                self.status.config(text="Current board has no valid sequential full-cover solution.")
        except Exception as exc:
            self.status.config(text=f"Invalid puzzle: {exc}")

    def solve(self):
        try:
            solver = ZipPuzzleSolver(self._board_to_solver_input(), h_walls=self.h_walls, v_walls=self.v_walls)
            solved = solver.solve(verify_unique=False)
            if solved:
                solved_board = solver.get_solution_board()
                self.solution_cells = {
                    (r, c)
                    for r in range(self.rows)
                    for c in range(self.cols)
                    if solved_board[r][c] != self.board[r][c]
                }
                self.board = solved_board
                self.fixed_cells = {(r, c) for r in range(self.rows) for c in range(self.cols) if self.clue_board[r][c] != 0}
                stats = solver.get_stats()
                self._draw_board()
                self.status.config(
                    text=(
                        f"Solved {self.rows}x{self.cols} sequential full-cover puzzle in {stats['time']:.3f}s, "
                        f"{stats['moves']} search moves."
                    )
                )
            else:
                self.status.config(text="No valid sequential full-cover solution found.")
        except Exception as exc:
            messagebox.showerror("Solve Error", str(exc), parent=self.root)

    def import_from_screenshot(self):
        if Image is None:
            messagebox.showerror(
                "Missing Dependency",
                "Pillow is required for screenshot import. Install it with: pip install pillow",
            )
            return

        image_path = filedialog.askopenfilename(
            title="Select Zip Screenshot",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp")],
        )
        if not image_path:
            return

        try:
            image = Image.open(image_path).convert("RGB")
            bounds = self._find_content_bounds(image)
            cropped = image.crop(bounds)
            rows, confidence = self._estimate_grid_size(cropped)
            cols = rows

            # Extract detected clues from the image
            clues, clue_confidence = self._extract_clues_from_image(cropped, rows, cols, (0, 0, cropped.size[0], cropped.size[1]))
            
            action = self._show_import_preview(
                clues=clues,
                rows=rows,
                cols=cols,
                confidence=confidence,
                source_label=Path(image_path).name,
                preview_image=cropped,
                clue_confidence=clue_confidence,
            )
            if action == "manual":
                manual_rows = simpledialog.askinteger("Board Rows", "Enter row count manually:", minvalue=2, parent=self.root)
                manual_cols = simpledialog.askinteger("Board Columns", "Enter column count manually:", minvalue=2, parent=self.root)
                if manual_rows is None or manual_cols is None:
                    return
                rows, cols = manual_rows, manual_cols
                clues, clue_confidence = self._extract_clues_from_image(cropped, rows, cols, (0, 0, cropped.size[0], cropped.size[1]))
                action = self._show_import_preview(
                    clues=clues,
                    rows=rows,
                    cols=cols,
                    confidence=confidence,
                    source_label=Path(image_path).name,
                    preview_image=cropped,
                    clue_confidence=clue_confidence,
                )

            if action != "use":
                return

            self._load_from_data({"rows": rows, "cols": cols, "clues": clues}, source_label=Path(image_path).name)
            self.status.config(text=f"Imported Zip board ({rows}x{cols}). Add numbers or solve.")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc), parent=self.root)

    def _show_import_preview(
        self,
        clues: List[List[int]],
        rows: int,
        cols: int,
        confidence: float,
        source_label: str,
        preview_image=None,
        clue_confidence: Optional[Dict[Tuple[int, int], float]] = None,
    ) -> str:
        preview = tk.Toplevel(self.root)
        preview.title("Zip Import Preview")
        preview.geometry("1160x760")
        preview.transient(self.root)
        preview.grab_set()

        container = ttk.Frame(preview, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        body = ttk.Frame(container)
        body.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(body)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        right_panel = ttk.Frame(body)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(14, 0))

        ttk.Label(left_panel, text="Detected Zip Puzzle", font=("Helvetica", 13, "bold")).pack(anchor="w")
        
        # Count detected clues
        detected_clues = sum(1 for row in clues for cell in row if cell > 0)
        avg_confidence = 0.0
        if clue_confidence:
            avg_confidence = sum(clue_confidence.values()) / len(clue_confidence) if clue_confidence else 0.0
        
        info_text = (
            f"Source: {source_label}\n"
            f"Detected size: {rows}x{cols} (grid confidence {confidence:.2f})\n"
        )
        if detected_clues > 0:
            info_text += f"Detected {detected_clues} clue(s) (avg confidence {avg_confidence:.2f})\n"
        info_text += (
            "Select cells and type clue numbers.\n"
            "Numbers should be unique and form ascending clues 1..N."
        )
        
        ttk.Label(
            left_panel,
            text=info_text,
            justify="left",
            wraplength=450,
        ).pack(anchor="w", pady=(6, 10))

        if ImageTk is not None and preview_image is not None:
            max_w = 450
            max_h = 220
            pw, ph = preview_image.size
            scale = min(max_w / max(1, pw), max_h / max(1, ph), 1.0)
            sw = max(1, int(pw * scale))
            sh = max(1, int(ph * scale))
            resized = preview_image.resize((sw, sh))
            preview_photo = ImageTk.PhotoImage(resized)
            setattr(preview, "_img_ref", preview_photo)
            ttk.Label(left_panel, text="Detected Board Crop").pack(anchor="w")
            ttk.Label(left_panel, image=preview_photo).pack(anchor="w", pady=(2, 8))

        cell_px = max(24, min(72, 640 // max(rows, cols)))
        canvas_w = cell_px * cols
        canvas_h = cell_px * rows
        canvas = tk.Canvas(right_panel, width=canvas_w, height=canvas_h, bg="#ffffff", highlightthickness=0)
        canvas.pack(anchor="n", pady=(2, 10))

        preview_clues = [row[:] for row in clues]
        selected_cells = {(0, 0)}
        selection_anchor = {"row": 0, "col": 0}
        cursor = {"row": 0, "col": 0}

        editor_row = ttk.Frame(left_panel)
        editor_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(editor_row, text="Label number:").pack(side=tk.LEFT)
        label_var = tk.StringVar(value="1")
        label_entry = ttk.Entry(editor_row, textvariable=label_var, width=8)
        label_entry.pack(side=tk.LEFT, padx=(6, 8))
        ttk.Button(editor_row, text="Apply", command=lambda: apply_label()).pack(side=tk.LEFT)
        ttk.Button(editor_row, text="Clear", command=lambda: apply_label(clear=True)).pack(side=tk.LEFT, padx=(8, 0))

        legend = tk.Canvas(left_panel, width=450, height=68, bg="#ffffff", highlightthickness=0)
        legend.pack(pady=(0, 8))

        def draw_legend():
            legend.delete("all")
            cols_per_row = 10
            sw = 44
            sh = 30
            for idx in range(20):
                rr = idx // cols_per_row
                cc = idx % cols_per_row
                x0 = cc * sw + 4
                y0 = rr * sh + 4
                x1 = x0 + sw - 8
                y1 = y0 + sh - 8
                legend.create_rectangle(x0, y0, x1, y1, fill=self._label_color(idx + 1), outline="#2a2a2a", width=1)
                legend.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(idx + 1), fill="#1a1a1a", font=("Helvetica", 9, "bold"))

        def redraw():
            canvas.delete("all")
            for r in range(rows):
                for c in range(cols):
                    x0 = c * cell_px
                    y0 = r * cell_px
                    x1 = x0 + cell_px
                    y1 = y0 + cell_px
                    value = preview_clues[r][c]
                    fill = self._label_color(value) if value != 0 else "#f7f7f7"
                    canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#cfc8bf", width=1)
                    if value != 0:
                        radius = max(11, cell_px // 3)
                        cx = (x0 + x1) / 2
                        cy = (y0 + y1) / 2
                        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#111111", outline="#111111")
                        canvas.create_text(cx, cy, text=str(value), fill="#ffffff", font=("Helvetica", max(10, cell_px // 4), "bold"))
                    if (r, c) in selected_cells:
                        canvas.create_rectangle(x0 + 4, y0 + 4, x1 - 4, y1 - 4, outline="#ffffff", width=3)
                    if cursor["row"] == r and cursor["col"] == c:
                        canvas.create_rectangle(x0 + 6, y0 + 6, x1 - 6, y1 - 6, outline="#111111", width=2)
            canvas.create_rectangle(0, 0, canvas_w, canvas_h, outline="#111111", width=2)

        def set_selection(target_row: int, target_col: int, extend: bool):
            target_row = max(0, min(rows - 1, target_row))
            target_col = max(0, min(cols - 1, target_col))
            cursor["row"] = target_row
            cursor["col"] = target_col
            if extend:
                ar, ac = selection_anchor["row"], selection_anchor["col"]
                r0 = min(ar, target_row)
                r1 = max(ar, target_row)
                c0 = min(ac, target_col)
                c1 = max(ac, target_col)
                selected_cells.clear()
                for rr in range(r0, r1 + 1):
                    for cc in range(c0, c1 + 1):
                        selected_cells.add((rr, cc))
            else:
                selection_anchor["row"] = target_row
                selection_anchor["col"] = target_col
                selected_cells.clear()
                selected_cells.add((target_row, target_col))
            label_var.set(str(preview_clues[target_row][target_col] if preview_clues[target_row][target_col] != 0 else 1))
            redraw()

        def apply_label(clear: bool = False):
            if clear:
                label = 0
            else:
                try:
                    label = int(label_var.get().strip())
                except ValueError:
                    messagebox.showerror("Invalid Label", "Label must be a whole number.", parent=preview)
                    return
                if label < 0:
                    messagebox.showerror("Invalid Label", "Label must be non-negative.", parent=preview)
                    return
            for r, c in selected_cells:
                preview_clues[r][c] = label
            redraw()

        def on_click(event):
            col = event.x // cell_px
            row = event.y // cell_px
            if 0 <= row < rows and 0 <= col < cols:
                shift_pressed = bool(event.state & 0x0001)
                set_selection(row, col, extend=shift_pressed)

        def on_arrow(event):
            delta = {
                "Up": (-1, 0),
                "Down": (1, 0),
                "Left": (0, -1),
                "Right": (0, 1),
            }.get(event.keysym)
            if delta is None:
                return
            dr, dc = delta
            shift_pressed = bool(event.state & 0x0001)
            set_selection(cursor["row"] + dr, cursor["col"] + dc, extend=shift_pressed)
            return "break"

        canvas.bind("<Button-1>", on_click)
        label_entry.bind("<Return>", lambda _event: apply_label())
        preview.bind("<Up>", on_arrow)
        preview.bind("<Down>", on_arrow)
        preview.bind("<Left>", on_arrow)
        preview.bind("<Right>", on_arrow)
        draw_legend()
        preview.focus_set()
        redraw()

        result = {"value": "cancel"}
        button_row = ttk.Frame(right_panel)
        button_row.pack(fill=tk.X, pady=(4, 0))

        def choose(value: str):
            result["value"] = value
            if value == "use":
                for r in range(rows):
                    for c in range(cols):
                        clues[r][c] = preview_clues[r][c]
            preview.destroy()

        ttk.Button(button_row, text="Use Detected", command=lambda: choose("use")).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Enter Size Manually", command=lambda: choose("manual")).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="Cancel", command=lambda: choose("cancel")).pack(side=tk.LEFT, padx=(8, 0))

        preview.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        preview.wait_window()
        return result["value"]


ZipGameUI = ZipUI

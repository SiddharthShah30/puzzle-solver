"""Tkinter UI for Tango puzzle."""

from __future__ import annotations

import colorsys
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

from .solver import TangoPuzzleSolver


class TangoUI:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Tango Solver")
        self.root.geometry("980x740")

        self.samples_dir = Path(__file__).parent / "samples"

        self.rows = 4
        self.cols = 4
        self.board: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.h_edges: List[List[int]] = [[0 for _ in range(max(0, self.cols - 1))] for _ in range(self.rows)]
        self.v_edges: List[List[int]] = [[0 for _ in range(self.cols)] for _ in range(max(0, self.rows - 1))]
        self.fixed_cells: Set[Tuple[int, int]] = set()
        self.solution_cells: Set[Tuple[int, int]] = set()
        self.cell_size = 90

        self._setup_ui()
        self._draw_board()

    def _setup_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Tango Puzzle", font=("Helvetica", 16, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Rules: Fill each cell with Symbol 1 or Symbol 2. No 3 equal adjacent in a row/column. "
                "Each row/column must stay as balanced as possible. "
                "Cells with '=' must match, and cells with 'X' must be opposite."
            ),
            wraplength=840,
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
        ttk.Button(right, text="Load Example", command=lambda: self.load_sample("tango_4x4_sample.json")).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Solve", command=self.solve).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Check Rules", command=self.check_current_board).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Clear User Entries", command=self.clear_user_entries).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Reset to Clues", command=self.reset_to_clues).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load Puzzle JSON", command=self.load_puzzle_json).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Save Puzzle JSON", command=self.save_puzzle_json).pack(fill=tk.X, pady=4)

        legend = ttk.Label(
            right,
            text="Left click cycle: Empty -> Symbol 1 (orange) -> Symbol 2 (blue moon) -> Empty",
            wraplength=300,
        )
        legend.pack(fill=tk.X, pady=(12, 0))

        self.status = ttk.Label(right, text="Ready", wraplength=300)
        self.status.pack(fill=tk.X, pady=(12, 0))

    def _default_checker_color(self, r: int, c: int) -> str:
        return "#f6f6f6" if (r + c) % 2 == 0 else "#e8e6e2"

    def _draw_symbol_one(self, x0: int, y0: int, x1: int, y1: int):
        pad = int((x1 - x0) * 0.22)
        self.canvas.create_oval(
            x0 + pad,
            y0 + pad,
            x1 - pad,
            y1 - pad,
            fill="#fbb71f",
            outline="#cc6f2b",
            width=3,
        )

    def _draw_symbol_two(self, x0: int, y0: int, x1: int, y1: int):
        w = x1 - x0
        h = y1 - y0
        pad = int(min(w, h) * 0.20)
        self.canvas.create_oval(
            x0 + pad,
            y0 + pad,
            x1 - pad,
            y1 - pad,
            fill="#4d87d8",
            outline="#225eaf",
            width=3,
        )
        self.canvas.create_oval(
            x0 + int(w * 0.46),
            y0 + int(h * 0.16),
            x1 - int(w * 0.12),
            y1 - int(h * 0.30),
            fill=self._default_checker_color(0, 0),
            outline=self._default_checker_color(0, 0),
            width=0,
        )

    def _draw_board(self):
        self.canvas.delete("all")
        board_width = max(320, self.cols * self.cell_size)
        board_height = max(320, self.rows * self.cell_size)
        self.cell_size = max(45, min(110, min(board_width // max(1, self.cols), board_height // max(1, self.rows))))
        board_px_w = self.cell_size * self.cols
        board_px_h = self.cell_size * self.rows

        self.canvas.config(width=board_px_w + 2, height=board_px_h + 2)

        for r in range(self.rows):
            for c in range(self.cols):
                x0 = c * self.cell_size
                y0 = r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size

                base_fill = self._default_checker_color(r, c)
                fill = "#dff0ff" if (r, c) in self.solution_cells and (r, c) not in self.fixed_cells else base_fill
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#d7d3ca", width=1)

                value = self.board[r][c]
                if value == 1:
                    self._draw_symbol_one(x0, y0, x1, y1)
                elif value == 2:
                    self._draw_symbol_two(x0, y0, x1, y1)

                if (r, c) in self.fixed_cells:
                    self.canvas.create_rectangle(x0 + 3, y0 + 3, x1 - 3, y1 - 3, outline="#4f5f75", width=2)

        for r in range(self.rows):
            for c in range(self.cols - 1):
                edge = self.h_edges[r][c]
                if edge == 0:
                    continue
                cx = (c + 1) * self.cell_size
                cy = r * self.cell_size + (self.cell_size // 2)
                marker = "=" if edge == 1 else "x"
                self.canvas.create_rectangle(cx - 10, cy - 9, cx + 10, cy + 9, fill="#f3f0ea", outline="#f3f0ea", width=0)
                self.canvas.create_text(cx, cy, text=marker, fill="#8c6e3f", font=("Helvetica", max(10, self.cell_size // 6), "bold"))

        for r in range(self.rows - 1):
            for c in range(self.cols):
                edge = self.v_edges[r][c]
                if edge == 0:
                    continue
                cx = c * self.cell_size + (self.cell_size // 2)
                cy = (r + 1) * self.cell_size
                marker = "=" if edge == 1 else "x"
                self.canvas.create_rectangle(cx - 10, cy - 9, cx + 10, cy + 9, fill="#f3f0ea", outline="#f3f0ea", width=0)
                self.canvas.create_text(cx, cy, text=marker, fill="#8c6e3f", font=("Helvetica", max(10, self.cell_size // 6), "bold"))

        self.canvas.create_rectangle(0, 0, board_px_w, board_px_h, outline="#222222", width=2)

    def _parse_edge_value(self, token) -> int:
        if isinstance(token, int):
            if token in (0, 1, 2):
                return token
            raise ValueError("Edge constraints must be 0 (none), 1 (=), or 2 (X)")

        text = str(token).strip().lower()
        if text in ("0", ".", "none", "-"):
            return 0
        if text in ("1", "=", "eq", "same", "s"):
            return 1
        if text in ("2", "x", "!=", "opp", "opposite", "o"):
            return 2
        raise ValueError(f"Invalid edge token: {token}")

    def _parse_edge_grid_text(self, raw_text: str, rows: int, cols: int) -> List[List[int]]:
        lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
        if rows == 0:
            return []
        if len(lines) != rows:
            raise ValueError(f"Expected {rows} edge rows, found {len(lines)}")

        parsed: List[List[int]] = []
        for line in lines:
            cells = [token for token in line.replace(",", " ").split(" ") if token]
            if len(cells) != cols:
                raise ValueError(f"Each edge row must have {cols} entries")
            parsed.append([self._parse_edge_value(token) for token in cells])
        return parsed

    def _edge_grid_to_text(self, grid: List[List[int]]) -> str:
        symbol = {0: ".", 1: "=", 2: "x"}
        return "\n".join(" ".join(symbol.get(v, ".") for v in row) for row in grid)

    def _normalize_edge_grid(self, grid, expected_rows: int, expected_cols: int, name: str) -> List[List[int]]:
        if expected_rows == 0:
            return []
        if grid is None:
            return [[0 for _ in range(expected_cols)] for _ in range(expected_rows)]
        if len(grid) != expected_rows or any(len(row) != expected_cols for row in grid):
            raise ValueError(f"{name} must be {expected_rows}x{expected_cols}")
        return [[self._parse_edge_value(value) for value in row] for row in grid]

    def _parse_grid_text(self, raw_text: str, rows: int, cols: int) -> List[List[int]]:
        lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
        if len(lines) != rows:
            raise ValueError(f"Expected {rows} rows, found {len(lines)}")

        parsed: List[List[int]] = []
        for line in lines:
            cells = [token for token in line.replace(',', ' ').split(' ') if token]
            if len(cells) != cols:
                raise ValueError(f"Each row must have {cols} integers")
            row_vals = [int(token) for token in cells]
            if any(v not in (0, 1, 2) for v in row_vals):
                raise ValueError("Only values 0, 1, 2 are allowed")
            parsed.append(row_vals)
        return parsed

    def new_puzzle_setup(self):
        setup = tk.Toplevel(self.root)
        setup.title("Tango Puzzle Setup")
        setup.geometry("760x700")
        setup.transient(self.root)
        setup.grab_set()

        container = ttk.Frame(setup, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Create Custom Tango Puzzle", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Enter any rectangular board size. 0=empty, 1=symbol1, 2=symbol2.\n"
                "Optional edge constraints: '=' same, 'x' opposite, '.' none."
            ),
            wraplength=610,
        ).pack(anchor="w", pady=(6, 8))

        size_row = ttk.Frame(container)
        size_row.pack(fill=tk.X)
        ttk.Label(size_row, text="Board size (rows x cols):").pack(side=tk.LEFT)
        rows_var = tk.StringVar(value="4")
        cols_var = tk.StringVar(value="4")
        ttk.Entry(size_row, textvariable=rows_var, width=6).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Label(size_row, text="x").pack(side=tk.LEFT)
        ttk.Entry(size_row, textvariable=cols_var, width=6).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(container, text="Clue grid (rows lines, cols integers each):").pack(anchor="w", pady=(12, 4))
        clue_text = tk.Text(container, height=16, width=72)
        clue_text.pack(fill=tk.BOTH, expand=True)
        clue_text.insert(
            "1.0",
            "1 0 2 0\n"
            "1 0 1 0\n"
            "0 2 0 1\n"
            "0 1 0 1\n",
        )

        edges_frame = ttk.Frame(container)
        edges_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        h_frame = ttk.Frame(edges_frame)
        h_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        ttk.Label(h_frame, text="Horizontal edges (rows x (cols-1)): ").pack(anchor="w")
        h_text = tk.Text(h_frame, height=8, width=32)
        h_text.pack(fill=tk.BOTH, expand=True)

        v_frame = ttk.Frame(edges_frame)
        v_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        ttk.Label(v_frame, text="Vertical edges ((rows-1) x cols):").pack(anchor="w")
        v_text = tk.Text(v_frame, height=8, width=32)
        v_text.pack(fill=tk.BOTH, expand=True)

        def fill_edge_defaults(*_args):
            try:
                r_count = max(2, int(rows_var.get()))
                c_count = max(2, int(cols_var.get()))
            except ValueError:
                return

            h_default = "\n".join(" ".join(["."] * max(1, c_count - 1)) for _ in range(r_count))
            v_default = "\n".join(" ".join(["."] * c_count) for _ in range(max(1, r_count - 1)))

            h_text.delete("1.0", tk.END)
            h_text.insert("1.0", h_default)
            v_text.delete("1.0", tk.END)
            v_text.insert("1.0", v_default)

        fill_edge_defaults()
        rows_var.trace_add("write", fill_edge_defaults)
        cols_var.trace_add("write", fill_edge_defaults)

        def apply_setup():
            try:
                rows = int(rows_var.get())
                cols = int(cols_var.get())
                if rows < 2 or cols < 2:
                    raise ValueError("Board dimensions must be at least 2x2")
                clues = self._parse_grid_text(clue_text.get("1.0", tk.END), rows, cols)
                h_edges = self._parse_edge_grid_text(h_text.get("1.0", tk.END), rows, cols - 1)
                v_edges = self._parse_edge_grid_text(v_text.get("1.0", tk.END), rows - 1, cols)
                self._load_from_data(
                    {"rows": rows, "cols": cols, "clues": clues, "h_edges": h_edges, "v_edges": v_edges},
                    source_label="custom setup",
                )
                setup.destroy()
            except Exception as exc:
                messagebox.showerror("Invalid Puzzle", str(exc), parent=setup)

        button_row = ttk.Frame(container)
        button_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_row, text="Apply Puzzle", command=apply_setup).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Cancel", command=setup.destroy).pack(side=tk.LEFT, padx=(8, 0))

    def _estimate_grid_size(self, image, min_size: int = 4, max_size: int = 16) -> Tuple[int, float]:
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
            for i in range(len(values)):
                l = max(0, i - radius)
                r = min(len(values) - 1, i + radius)
                out[i] = (prefix[r + 1] - prefix[l]) / (r - l + 1)
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

            threshold = p_min + 0.58 * (p_max - p_min)

            def collect(local_threshold: float) -> List[int]:
                return [
                    idx
                    for idx in range(1, len(profile) - 1)
                    if profile[idx] >= local_threshold and profile[idx] >= profile[idx - 1] and profile[idx] >= profile[idx + 1]
                ]

            candidates = collect(threshold)
            if not candidates:
                candidates = collect(p_min + 0.45 * (p_max - p_min))

            min_sep = max(2, int(len(profile) / 30))
            chosen: List[int] = []
            for idx in sorted(candidates, key=lambda i: profile[i], reverse=True):
                if all(abs(idx - prev) >= min_sep for prev in chosen):
                    chosen.append(idx)
            return len(chosen)

        rough_rows = max(2, detect_peak_count(h_profile) - 1)
        rough_cols = max(2, detect_peak_count(v_profile) - 1)

        def border_pair(profile: List[float], length: int) -> Tuple[int, int]:
            zone = max(8, int(length * 0.20))
            left_idx = 1 + max(range(len(profile[1:zone])), key=lambda i: profile[1 + i])
            right_start = max(1, length - zone)
            right_idx = right_start + max(range(len(profile[right_start:length - 1])), key=lambda i: profile[right_start + i])
            if right_idx - left_idx < int(length * 0.45):
                return 1, length - 1
            return left_idx, right_idx

        def mean_at(profile: List[float], indices: List[int]) -> float:
            if not indices:
                return 0.0
            return sum(profile[i] for i in indices) / len(indices)

        def axis_score(profile: List[float], length: int, n: int) -> float:
            left, right = border_pair(profile, length)
            step = (right - left) / float(n)
            if step < 3:
                return -1e9

            best = -1e9
            for jitter in (-2, -1, 0, 1, 2):
                lines = []
                gaps = []
                for i in range(n + 1):
                    p = int(round(left + jitter + i * step))
                    lines.append(min(max(1, p), length - 1))
                for i in range(n):
                    p = int(round(left + jitter + (i + 0.5) * step))
                    gaps.append(min(max(1, p), length - 1))

                line_strength = mean_at(profile, lines)
                gap_strength = mean_at(profile, gaps)
                score = (line_strength - 0.80 * gap_strength) + 0.20 * line_strength
                best = max(best, score)
            return best

        scored: List[Tuple[int, float]] = []
        for n in range(max(2, min_size), max(min_size, max_size) + 1):
            s = (axis_score(v_profile, width, n) + axis_score(h_profile, height, n)) / 2.0
            scored.append((n, s))

        scored.sort(key=lambda item: item[1], reverse=True)
        best_n, best_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else -1e9
        confidence = 1.0 + max(0.0, best_score - second_score) / max(abs(second_score), 1.0)
        return best_n, confidence

    def _estimate_board_shape(
        self,
        image,
        min_size: int = 2,
        max_size: int = 16,
    ) -> Tuple[int, int, Tuple[int, int, int, int], float, Dict[str, List[Tuple[int, float]]]]:
        width, height = image.size
        gray = image.convert("L")
        px = gray.load()

        v_profile = [0.0 for _ in range(width)]
        h_profile = [0.0 for _ in range(height)]

        for x in range(1, width):
            total = 0.0
            for y in range(height):
                total += abs(int(px[x, y]) - int(px[x - 1, y]))
            v_profile[x] = total / max(1, height)

        for y in range(1, height):
            total = 0.0
            for x in range(width):
                total += abs(int(px[x, y]) - int(px[x, y - 1]))
            h_profile[y] = total / max(1, width)

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

        def strongest_peaks(profile: List[float]) -> List[int]:
            if len(profile) < 7:
                return []

            p_min = min(profile)
            p_max = max(profile)
            if p_max <= p_min:
                return []

            threshold = p_min + 0.52 * (p_max - p_min)
            candidates = [
                idx
                for idx in range(2, len(profile) - 2)
                if profile[idx] >= threshold
                and profile[idx] >= profile[idx - 1]
                and profile[idx] >= profile[idx + 1]
            ]

            min_sep = max(2, int(len(profile) / 28))
            chosen: List[int] = []
            for idx in sorted(candidates, key=lambda i: profile[i], reverse=True):
                if all(abs(idx - prev) >= min_sep for prev in chosen):
                    chosen.append(idx)

            chosen.sort()
            return chosen

        def periodicity_estimate(profile: List[float], length: int) -> Optional[int]:
            values = profile[:]
            mean = sum(values) / max(1, len(values))
            values = [v - mean for v in values]

            lag_min = max(3, int(length / max_size))
            lag_max = max(lag_min + 1, int(length / max(min_size, 2)))
            lag_max = min(lag_max, max(4, length - 4))
            if lag_min >= lag_max:
                return None

            best_lag = None
            best_corr = -1e9
            for lag in range(lag_min, lag_max + 1):
                limit = len(values) - lag
                if limit <= 4:
                    continue
                corr = 0.0
                energy_a = 0.0
                energy_b = 0.0
                for i in range(limit):
                    a = values[i]
                    b = values[i + lag]
                    corr += a * b
                    energy_a += a * a
                    energy_b += b * b
                if energy_a <= 1e-9 or energy_b <= 1e-9:
                    continue
                norm = corr / ((energy_a ** 0.5) * (energy_b ** 0.5))
                if norm > best_corr:
                    best_corr = norm
                    best_lag = lag

            if best_lag is None:
                return None

            count = int(round(length / float(best_lag)))
            if count < min_size or count > max_size:
                return None
            return count

        rough_rows = max(2, detect_peak_count(h_profile) - 1)
        rough_cols = max(2, detect_peak_count(v_profile) - 1)
        peak_rows = strongest_peaks(h_profile)
        peak_cols = strongest_peaks(v_profile)

        periodic_rows = periodicity_estimate(h_profile, height)
        periodic_cols = periodicity_estimate(v_profile, width)

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
                best = max(best, score)
            return best, (left, right)

        row_scored = []
        col_scored = []
        for n in range(max(2, min_size), max(min_size, max_size) + 1):
            row_score, row_bounds = axis_score(h_profile, height, n)
            col_score, col_bounds = axis_score(v_profile, width, n)
            row_scored.append((n, row_score - 0.08 * abs(n - rough_rows), row_bounds))
            col_scored.append((n, col_score - 0.08 * abs(n - rough_cols), col_bounds))

        row_scored.sort(key=lambda item: item[1], reverse=True)
        col_scored.sort(key=lambda item: item[1], reverse=True)

        row_lookup = {n: (score, bounds) for n, score, bounds in row_scored}
        col_lookup = {n: (score, bounds) for n, score, bounds in col_scored}

        row_candidates = {row_scored[0][0], row_scored[1][0] if len(row_scored) > 1 else row_scored[0][0], rough_rows}
        col_candidates = {col_scored[0][0], col_scored[1][0] if len(col_scored) > 1 else col_scored[0][0], rough_cols}

        if periodic_rows is not None:
            row_candidates.add(periodic_rows)
        if periodic_cols is not None:
            col_candidates.add(periodic_cols)

        if len(peak_rows) >= 3:
            row_spacings = [peak_rows[i + 1] - peak_rows[i] for i in range(len(peak_rows) - 1)]
            row_step = sum(row_spacings) / max(1, len(row_spacings))
            if row_step > 1:
                from_peaks = int(round((peak_rows[-1] - peak_rows[0]) / row_step))
                if min_size <= from_peaks <= max_size:
                    row_candidates.add(from_peaks)

        if len(peak_cols) >= 3:
            col_spacings = [peak_cols[i + 1] - peak_cols[i] for i in range(len(peak_cols) - 1)]
            col_step = sum(col_spacings) / max(1, len(col_spacings))
            if col_step > 1:
                from_peaks = int(round((peak_cols[-1] - peak_cols[0]) / col_step))
                if min_size <= from_peaks <= max_size:
                    col_candidates.add(from_peaks)

        def select_count(
            candidates: Set[int],
            lookup: dict,
            rough_value: int,
            periodic_value: Optional[int],
            primary_weight: float,
        ) -> Tuple[int, float, Tuple[int, int]]:
            best_choice = None
            best_metric = -1e9
            for n in candidates:
                if n not in lookup:
                    continue
                score, bounds = lookup[n]
                metric = score
                metric -= 0.05 * abs(n - rough_value)
                if periodic_value is not None:
                    metric -= 0.04 * abs(n - periodic_value)
                metric += primary_weight if n == rough_value else 0.0
                if best_choice is None or metric > best_metric:
                    best_choice = (n, score, bounds)
                    best_metric = metric

            if best_choice is None:
                n, score, bounds = max(lookup.items(), key=lambda item: item[1][0])[0], 0.0, (1, 1)
                score, bounds = lookup[n]
                return n, score, bounds

            return best_choice

        best_rows, best_row_score, (top, bottom) = select_count(
            row_candidates,
            row_lookup,
            rough_rows,
            periodic_rows,
            primary_weight=0.06,
        )
        best_cols, best_col_score, (left, right) = select_count(
            col_candidates,
            col_lookup,
            rough_cols,
            periodic_cols,
            primary_weight=0.06,
        )

        second_row_score = row_scored[1][1] if len(row_scored) > 1 else -1e9
        second_col_score = col_scored[1][1] if len(col_scored) > 1 else -1e9
        confidence = 1.0 + min(
            max(0.0, best_row_score - second_row_score) / max(abs(second_row_score), 1.0),
            max(0.0, best_col_score - second_col_score) / max(abs(second_col_score), 1.0),
        )

        row_top = [(n, score) for n, score, _ in row_scored[:3]]
        col_top = [(n, score) for n, score, _ in col_scored[:3]]
        candidate_info = {
            "row_candidates": row_top,
            "col_candidates": col_top,
        }

        return best_rows, best_cols, (left, top, right, bottom), confidence, candidate_info

    def _detect_symbol_features(self, image, bounds: Tuple[int, int, int, int], rows: int, cols: int):
        left, top, right, bottom = bounds
        board_w = max(1, right - left)
        board_h = max(1, bottom - top)
        cell_w = board_w / cols
        cell_h = board_h / rows

        features = []
        for r in range(rows):
            for c in range(cols):
                x0 = int(left + c * cell_w)
                y0 = int(top + r * cell_h)
                x1 = int(left + (c + 1) * cell_w)
                y1 = int(top + (r + 1) * cell_h)
                x0 = max(0, min(image.size[0] - 1, x0))
                y0 = max(0, min(image.size[1] - 1, y0))
                x1 = max(x0 + 1, min(image.size[0], x1))
                y1 = max(y0 + 1, min(image.size[1], y1))

                margin_x = max(3, int((x1 - x0) * 0.18))
                margin_y = max(3, int((y1 - y0) * 0.18))
                sample_x0 = x0 + margin_x
                sample_y0 = y0 + margin_y
                sample_x1 = x1 - margin_x
                sample_y1 = y1 - margin_y
                if sample_x1 <= sample_x0 or sample_y1 <= sample_y0:
                    sample_x0, sample_y0, sample_x1, sample_y1 = x0, y0, x1, y1

                inset_x = max(3, int((x1 - x0) * 0.24))
                inset_y = max(3, int((y1 - y0) * 0.24))
                corner_points = [
                    image.getpixel((min(image.size[0] - 1, x0 + inset_x), min(image.size[1] - 1, y0 + inset_y))),
                    image.getpixel((max(0, x1 - inset_x - 1), min(image.size[1] - 1, y0 + inset_y))),
                    image.getpixel((min(image.size[0] - 1, x0 + inset_x), max(0, y1 - inset_y - 1))),
                    image.getpixel((max(0, x1 - inset_x - 1), max(0, y1 - inset_y - 1))),
                ]
                bg = tuple(sum(point[idx] for point in corner_points) / len(corner_points) for idx in range(3))

                fg_pixels = []
                total_pixels = 0
                for y in range(sample_y0, sample_y1):
                    for x in range(sample_x0, sample_x1):
                        r_, g_, b_ = image.getpixel((x, y))
                        dr = r_ - bg[0]
                        dg = g_ - bg[1]
                        db = b_ - bg[2]
                        dist = (dr * dr + dg * dg + db * db) ** 0.5
                        total_pixels += 1
                        if dist > 32:
                            fg_pixels.append((x, y, r_, g_, b_))

                fg_fraction = len(fg_pixels) / max(1, total_pixels)
                if fg_fraction < 0.02 or fg_fraction > 0.55:
                    features.append({"occupied": False, "feature": None})
                    continue

                min_x = min(p[0] for p in fg_pixels)
                max_x = max(p[0] for p in fg_pixels)
                min_y = min(p[1] for p in fg_pixels)
                max_y = max(p[1] for p in fg_pixels)
                bbox_w = max(1, max_x - min_x + 1)
                bbox_h = max(1, max_y - min_y + 1)
                aspect = bbox_w / bbox_h

                avg_r = sum(p[2] for p in fg_pixels) / len(fg_pixels)
                avg_g = sum(p[3] for p in fg_pixels) / len(fg_pixels)
                avg_b = sum(p[4] for p in fg_pixels) / len(fg_pixels)
                cx = sum(p[0] for p in fg_pixels) / len(fg_pixels)
                cy = sum(p[1] for p in fg_pixels) / len(fg_pixels)
                spread_x = sum(abs(p[0] - cx) for p in fg_pixels) / len(fg_pixels)
                spread_y = sum(abs(p[1] - cy) for p in fg_pixels) / len(fg_pixels)

                features.append({
                    "occupied": True,
                    "feature": [avg_r, avg_g, avg_b, fg_fraction * 255.0, aspect * 80.0, spread_x + spread_y],
                })

        return features

    def _cluster_binary_features(self, features):
        vectors = [entry["feature"] for entry in features if entry["occupied"] and entry["feature"] is not None]
        if not vectors:
            raise ValueError("Could not detect any symbols in the screenshot")
        if len(vectors) == 1:
            return [1 if entry["occupied"] else 0 for entry in features]

        centers = [vectors[0][:], vectors[-1][:]]

        for _ in range(8):
            groups = {0: [], 1: []}
            for vector in vectors:
                distances = [sum((vector[i] - centers[idx][i]) ** 2 for i in range(len(vector))) for idx in range(2)]
                group = 0 if distances[0] <= distances[1] else 1
                groups[group].append(vector)
            for idx in (0, 1):
                if groups[idx]:
                    centers[idx] = [sum(vector[i] for vector in groups[idx]) / len(groups[idx]) for i in range(len(centers[idx]))]

        labels = []
        for entry in features:
            if not entry["occupied"]:
                labels.append(0)
                continue
            vector = entry["feature"]
            distances = [sum((vector[i] - centers[idx][i]) ** 2 for i in range(len(vector))) for idx in range(2)]
            labels.append(1 if distances[0] <= distances[1] else 2)

        return labels

    def _extract_clues_from_image(self, image, rows: int, cols: int, bounds: Tuple[int, int, int, int]) -> List[List[int]]:
        clues = [[0 for _ in range(cols)] for _ in range(rows)]
        detected = 0
        left, top, right, bottom = bounds
        board_w = max(1, right - left)
        board_h = max(1, bottom - top)
        cell_w = board_w / cols
        cell_h = board_h / rows

        for r in range(rows):
            for c in range(cols):
                x0 = int(left + c * cell_w)
                y0 = int(top + r * cell_h)
                x1 = int(left + (c + 1) * cell_w)
                y1 = int(top + (r + 1) * cell_h)
                x0 = max(0, min(image.size[0] - 1, x0))
                y0 = max(0, min(image.size[1] - 1, y0))
                x1 = max(x0 + 1, min(image.size[0], x1))
                y1 = max(y0 + 1, min(image.size[1], y1))
                clues[r][c] = self._classify_symbol_cell(image, x0, y0, x1, y1)
                if clues[r][c] != 0:
                    detected += 1

        if detected == 0:
            features = self._detect_symbol_features(image, bounds, rows, cols)
            labels = self._cluster_binary_features(features)
            idx = 0
            for r in range(rows):
                for c in range(cols):
                    clues[r][c] = labels[idx]
                    idx += 1

        return clues

    def _classify_edge_symbol(self, image, x0: int, y0: int, x1: int, y1: int) -> Tuple[int, float]:
        """Classify edge marker patch: (value, confidence), value in {0,1,2}."""
        w = max(1, x1 - x0)
        h = max(1, y1 - y0)
        if w < 4 or h < 4:
            return 0, 0.0

        border_samples = []
        for x in range(x0, x1):
            border_samples.append(image.getpixel((x, y0)))
            border_samples.append(image.getpixel((x, y1 - 1)))
        for y in range(y0, y1):
            border_samples.append(image.getpixel((x0, y)))
            border_samples.append(image.getpixel((x1 - 1, y)))

        if not border_samples:
            return 0, 0.0

        bg = tuple(sum(p[i] for p in border_samples) / len(border_samples) for i in range(3))

        fg_points = []
        for y in range(y0, y1):
            for x in range(x0, x1):
                r, g, b = image.getpixel((x, y))
                dist = ((r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2) ** 0.5
                bright = (r + g + b) / 3.0
                if dist > 28 and bright < ((bg[0] + bg[1] + bg[2]) / 3.0 - 6):
                    fg_points.append((x, y))

        area = w * h
        fg_frac = len(fg_points) / max(1, area)
        if fg_frac < 0.04 or fg_frac > 0.55:
            return 0, 0.0

        top_band = 0
        bottom_band = 0
        diag1 = 0
        diag2 = 0

        for x, y in fg_points:
            nx = (x - x0) / float(max(1, w - 1))
            ny = (y - y0) / float(max(1, h - 1))
            if 0.12 <= nx <= 0.88:
                if abs(ny - 0.35) <= 0.13:
                    top_band += 1
                if abs(ny - 0.65) <= 0.13:
                    bottom_band += 1

            if 0.10 <= nx <= 0.90 and 0.10 <= ny <= 0.90:
                if abs(ny - nx) <= 0.18:
                    diag1 += 1
                if abs(ny - (1.0 - nx)) <= 0.18:
                    diag2 += 1

        fg_count = max(1, len(fg_points))
        eq_strength = min(top_band, bottom_band) / fg_count + 0.35 * (top_band + bottom_band) / fg_count
        x_strength = min(diag1, diag2) / fg_count + 0.35 * (diag1 + diag2) / fg_count

        if x_strength >= 0.28 and x_strength > eq_strength * 1.16:
            return 2, x_strength - eq_strength
        if eq_strength >= 0.28 and eq_strength > x_strength * 1.12:
            return 1, eq_strength - x_strength
        return 0, 0.0

    def _extract_edges_from_image(
        self,
        image,
        rows: int,
        cols: int,
        bounds: Tuple[int, int, int, int],
    ) -> Tuple[List[List[int]], List[List[int]], List[Tuple[str, int, int, float]]]:
        left, top, right, bottom = bounds
        board_w = max(1, right - left)
        board_h = max(1, bottom - top)
        cell_w = board_w / cols
        cell_h = board_h / rows

        h_edges = [[0 for _ in range(max(0, cols - 1))] for _ in range(rows)]
        v_edges = [[0 for _ in range(cols)] for _ in range(max(0, rows - 1))]
        edge_candidates: List[Tuple[str, int, int, float]] = []

        for r in range(rows):
            for c in range(cols - 1):
                cx = int(round(left + (c + 1) * cell_w))
                cy = int(round(top + (r + 0.5) * cell_h))
                box_w = max(8, int(cell_w * 0.36))
                box_h = max(8, int(cell_h * 0.30))
                x0 = max(0, cx - box_w // 2)
                y0 = max(0, cy - box_h // 2)
                x1 = min(image.size[0], cx + box_w // 2)
                y1 = min(image.size[1], cy + box_h // 2)
                value, conf = self._classify_edge_symbol(image, x0, y0, x1, y1)
                h_edges[r][c] = value
                if value != 0:
                    edge_candidates.append(("h", r, c, conf))

        for r in range(rows - 1):
            for c in range(cols):
                cx = int(round(left + (c + 0.5) * cell_w))
                cy = int(round(top + (r + 1) * cell_h))
                box_w = max(8, int(cell_w * 0.30))
                box_h = max(8, int(cell_h * 0.36))
                x0 = max(0, cx - box_w // 2)
                y0 = max(0, cy - box_h // 2)
                x1 = min(image.size[0], cx + box_w // 2)
                y1 = min(image.size[1], cy + box_h // 2)
                value, conf = self._classify_edge_symbol(image, x0, y0, x1, y1)
                v_edges[r][c] = value
                if value != 0:
                    edge_candidates.append(("v", r, c, conf))

        return h_edges, v_edges, edge_candidates

    def _is_satisfiable_with_constraints(
        self,
        clues: List[List[int]],
        h_edges: List[List[int]],
        v_edges: List[List[int]],
    ) -> bool:
        try:
            solver = TangoPuzzleSolver(clues, h_edges=h_edges, v_edges=v_edges)
        except ValueError:
            return False
        board_copy = [row[:] for row in clues]
        return solver._propagate(board_copy)

    def _sanitize_detected_edges(
        self,
        clues: List[List[int]],
        h_edges: List[List[int]],
        v_edges: List[List[int]],
        edge_candidates: List[Tuple[str, int, int, float]],
    ) -> Tuple[List[List[int]], List[List[int]]]:
        if self._is_satisfiable_with_constraints(clues, h_edges, v_edges):
            return h_edges, v_edges

        ordered = sorted(edge_candidates, key=lambda item: item[3])
        h_work = [row[:] for row in h_edges]
        v_work = [row[:] for row in v_edges]

        for axis, r, c, _ in ordered:
            if axis == "h":
                h_work[r][c] = 0
            else:
                v_work[r][c] = 0

            if self._is_satisfiable_with_constraints(clues, h_work, v_work):
                return h_work, v_work

        return h_work, v_work

    def _classify_symbol_cell(self, image, x0: int, y0: int, x1: int, y1: int) -> int:
        orange_hits = 0
        blue_hits = 0

        dx = max(1, (x1 - x0) // 16)
        dy = max(1, (y1 - y0) // 16)

        cx0 = x0 + int((x1 - x0) * 0.18)
        cy0 = y0 + int((y1 - y0) * 0.18)
        cx1 = x1 - int((x1 - x0) * 0.18)
        cy1 = y1 - int((y1 - y0) * 0.18)

        for y in range(cy0, cy1, dy):
            for x in range(cx0, cx1, dx):
                r, g, b = image.getpixel((x, y))
                h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                hue = h * 360.0
                sat = s * 255.0
                val = v * 255.0

                if sat < 70 or val < 60:
                    continue

                if 20 <= hue <= 55 and r > 170 and g > 100 and b < 120:
                    orange_hits += 1
                elif 190 <= hue <= 235 and b > 130 and r < 140:
                    blue_hits += 1

        if orange_hits >= max(3, blue_hits + 1):
            return 1
        if blue_hits >= max(3, orange_hits + 1):
            return 2
        return 0

    def import_from_screenshot(self):
        if Image is None:
            messagebox.showerror(
                "Missing Dependency",
                "Pillow is required for screenshot import. Install it with: pip install pillow",
            )
            return

        image_path = filedialog.askopenfilename(
            title="Select Tango Screenshot",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp")],
        )
        if not image_path:
            return

        try:
            image = Image.open(image_path).convert("RGB")
            bounds = self._find_content_bounds(image)
            cropped = image.crop(bounds)
            rows, cols, inner_bounds, confidence, candidate_info = self._estimate_board_shape(cropped)

            clues = self._extract_clues_from_image(cropped, rows, cols, inner_bounds)
            h_edges, v_edges, edge_candidates = self._extract_edges_from_image(cropped, rows, cols, inner_bounds)
            h_edges, v_edges = self._sanitize_detected_edges(clues, h_edges, v_edges, edge_candidates)
            action = self._show_import_preview(
                clues=clues,
                h_edges=h_edges,
                v_edges=v_edges,
                rows=rows,
                cols=cols,
                confidence=confidence,
                source_label=Path(image_path).name,
                preview_image=cropped,
                candidate_info=candidate_info,
            )

            if action == "manual":
                manual_rows = simpledialog.askinteger(
                    "Board Rows",
                    "Enter row count manually:",
                    minvalue=2,
                    parent=self.root,
                )
                manual_cols = simpledialog.askinteger(
                    "Board Columns",
                    "Enter column count manually:",
                    minvalue=2,
                    parent=self.root,
                )
                if manual_rows is None or manual_cols is None:
                    return
                if manual_rows < 2 or manual_cols < 2:
                    raise ValueError("Board dimensions must be at least 2x2")
                rows, cols = manual_rows, manual_cols
                clues = self._extract_clues_from_image(cropped, rows, cols, inner_bounds)
                h_edges, v_edges, edge_candidates = self._extract_edges_from_image(cropped, rows, cols, inner_bounds)
                h_edges, v_edges = self._sanitize_detected_edges(clues, h_edges, v_edges, edge_candidates)
                action = self._show_import_preview(
                    clues=clues,
                    h_edges=h_edges,
                    v_edges=v_edges,
                    rows=rows,
                    cols=cols,
                    confidence=confidence,
                    source_label=Path(image_path).name,
                    preview_image=cropped,
                    candidate_info=candidate_info,
                )

            if action != "use":
                return

            self._load_from_data(
                {
                    "rows": rows,
                    "cols": cols,
                    "clues": clues,
                    "h_edges": h_edges,
                    "v_edges": v_edges,
                },
                source_label=Path(image_path).name,
            )
            self.status.config(text=f"Imported clues from screenshot ({rows}x{cols}).")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc), parent=self.root)

    def _show_import_preview(
        self,
        clues: List[List[int]],
        h_edges: List[List[int]],
        v_edges: List[List[int]],
        rows: int,
        cols: int,
        confidence: float,
        source_label: str,
        preview_image=None,
        candidate_info: Optional[Dict[str, List[Tuple[int, float]]]] = None,
    ) -> str:
        preview = tk.Toplevel(self.root)
        preview.title("Tango Import Preview")
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

        ttk.Label(left_panel, text="Detected Tango Puzzle", font=("Helvetica", 13, "bold")).pack(anchor="w")
        ttk.Label(
            left_panel,
            text=(
                f"Source: {source_label}\n"
                f"Detected size: {rows}x{cols} (confidence {confidence:.2f})\n"
                "Click any cell to cycle Empty -> Symbol 1 -> Symbol 2.\n"
                "Click between cells to cycle edge: none -> '=' -> 'x' -> none."
            ),
            justify="left",
            wraplength=450,
        ).pack(anchor="w", pady=(6, 10))

        if candidate_info:
            row_candidates = candidate_info.get("row_candidates", [])[:3]
            col_candidates = candidate_info.get("col_candidates", [])[:3]

            def format_axis(prefix: str, values: List[Tuple[int, float]]) -> str:
                if not values:
                    return f"{prefix}: n/a"
                top = values[0][1]
                parts = []
                for n, score in values:
                    rel = 1.0 if top == 0 else (score / top)
                    parts.append(f"{n} ({rel:.2f})")
                return f"{prefix}: " + ", ".join(parts)

            candidate_text = (
                "Top detected size candidates (relative confidence):\n"
                + format_axis("Rows", row_candidates)
                + "\n"
                + format_axis("Cols", col_candidates)
            )
            ttk.Label(left_panel, text=candidate_text, justify="left", wraplength=450).pack(anchor="w", pady=(0, 8))

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
        preview_h_edges = [row[:] for row in h_edges]
        preview_v_edges = [row[:] for row in v_edges]

        marker_font = ("Helvetica", max(10, cell_px // 4), "bold")

        def draw_edge_marker(cx: int, cy: int, value: int):
            if value == 0:
                return
            marker = "=" if value == 1 else "x"
            canvas.create_rectangle(cx - 9, cy - 8, cx + 9, cy + 8, fill="#f3f0ea", outline="#f3f0ea", width=0)
            canvas.create_text(cx, cy, text=marker, fill="#8c6e3f", font=marker_font)

        def redraw():
            canvas.delete("all")
            for r in range(rows):
                for c in range(cols):
                    x0 = c * cell_px
                    y0 = r * cell_px
                    x1 = x0 + cell_px
                    y1 = y0 + cell_px
                    fill = self._default_checker_color(r, c)
                    canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#cfc8bf", width=1)

                    value = preview_clues[r][c]
                    if value == 1:
                        pad = int(cell_px * 0.22)
                        canvas.create_oval(
                            x0 + pad,
                            y0 + pad,
                            x1 - pad,
                            y1 - pad,
                            fill="#fbb71f",
                            outline="#cc6f2b",
                            width=2,
                        )
                    elif value == 2:
                        pad = int(cell_px * 0.20)
                        canvas.create_oval(
                            x0 + pad,
                            y0 + pad,
                            x1 - pad,
                            y1 - pad,
                            fill="#4d87d8",
                            outline="#225eaf",
                            width=2,
                        )
                        canvas.create_oval(
                            x0 + int(cell_px * 0.46),
                            y0 + int(cell_px * 0.16),
                            x1 - int(cell_px * 0.12),
                            y1 - int(cell_px * 0.30),
                            fill=fill,
                            outline=fill,
                            width=0,
                        )

            for r in range(rows):
                for c in range(cols - 1):
                    cx = (c + 1) * cell_px
                    cy = int((r + 0.5) * cell_px)
                    draw_edge_marker(cx, cy, preview_h_edges[r][c])

            for r in range(rows - 1):
                for c in range(cols):
                    cx = int((c + 0.5) * cell_px)
                    cy = (r + 1) * cell_px
                    draw_edge_marker(cx, cy, preview_v_edges[r][c])

            canvas.create_rectangle(0, 0, canvas_w, canvas_h, outline="#111111", width=2)

        def hit_edge(x: int, y: int):
            radius = max(8, int(cell_px * 0.17))
            for r in range(rows):
                for c in range(cols - 1):
                    cx = (c + 1) * cell_px
                    cy = int((r + 0.5) * cell_px)
                    if abs(x - cx) <= radius and abs(y - cy) <= radius:
                        return ("h", r, c)
            for r in range(rows - 1):
                for c in range(cols):
                    cx = int((c + 0.5) * cell_px)
                    cy = (r + 1) * cell_px
                    if abs(x - cx) <= radius and abs(y - cy) <= radius:
                        return ("v", r, c)
            return None

        def on_click(event):
            edge_hit = hit_edge(event.x, event.y)
            if edge_hit is not None:
                axis, r, c = edge_hit
                if axis == "h":
                    preview_h_edges[r][c] = (preview_h_edges[r][c] + 1) % 3
                else:
                    preview_v_edges[r][c] = (preview_v_edges[r][c] + 1) % 3
                redraw()
                return

            col = event.x // cell_px
            row = event.y // cell_px
            if 0 <= row < rows and 0 <= col < cols:
                preview_clues[row][col] = (preview_clues[row][col] + 1) % 3
                redraw()

        canvas.bind("<Button-1>", on_click)
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
                for r in range(rows):
                    for c in range(cols - 1):
                        h_edges[r][c] = preview_h_edges[r][c]
                for r in range(rows - 1):
                    for c in range(cols):
                        v_edges[r][c] = preview_v_edges[r][c]
            preview.destroy()

        ttk.Button(button_row, text="Use Detected", command=lambda: choose("use")).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Enter Size Manually", command=lambda: choose("manual")).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="Cancel", command=lambda: choose("cancel")).pack(side=tk.LEFT, padx=(8, 0))

        preview.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        preview.wait_window()
        return result["value"]

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

    def on_canvas_click(self, event):
        if self.rows == 0 or self.cols == 0:
            return

        c = event.x // self.cell_size
        r = event.y // self.cell_size
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return

        if (r, c) in self.fixed_cells:
            self.status.config(text="Fixed clue cell. Use reset/new puzzle to modify clues.")
            return

        self.board[r][c] = (self.board[r][c] + 1) % 3
        self.solution_cells.clear()
        self._draw_board()

    def _load_from_data(self, data: dict, source_label: str):
        if "clues" not in data:
            raise ValueError("Puzzle JSON must include a 'clues' grid")

        clues = data["clues"]
        rows = data.get("rows")
        cols = data.get("cols")

        if rows is None or cols is None:
            if "size" in data:
                rows = cols = int(data["size"])
            else:
                rows = len(clues)
                cols = len(clues[0]) if clues else 0

        if rows < 2 or cols < 2:
            raise ValueError("Board dimensions must be at least 2x2")
        if len(clues) != rows or any(len(row) != cols for row in clues):
            raise ValueError("Clues grid must match the declared rows and columns")

        for row in clues:
            for value in row:
                if value not in (0, 1, 2):
                    raise ValueError("Clues must contain only 0, 1, or 2")

        self.rows = rows
        self.cols = cols
        self.board = [row[:] for row in clues]
        self.h_edges = self._normalize_edge_grid(data.get("h_edges"), rows, max(0, cols - 1), "h_edges")
        self.v_edges = self._normalize_edge_grid(data.get("v_edges"), max(0, rows - 1), cols, "v_edges")
        self.fixed_cells = {(r, c) for r in range(rows) for c in range(cols) if self.board[r][c] != 0}
        self.solution_cells.clear()
        self._draw_board()
        self.status.config(text=f"Loaded Tango puzzle from {source_label} ({rows}x{cols}).")

    def load_sample(self, filename: str):
        path = self.samples_dir / filename
        if not path.exists():
            messagebox.showerror("Missing Sample", f"Could not find {filename}")
            return
        self._load_from_file(path)

    def load_puzzle_json(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.samples_dir,
            filetypes=[("JSON files", "*.json")],
        )
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
            "h_edges": [row[:] for row in self.h_edges],
            "v_edges": [row[:] for row in self.v_edges],
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
        self.board = [[self.board[r][c] if (r, c) in self.fixed_cells else 0 for c in range(self.cols)] for r in range(self.rows)]
        self.solution_cells.clear()
        self._draw_board()
        self.status.config(text="Reset board to original clues.")

    def _board_valid_now(self) -> bool:
        try:
            solver = TangoPuzzleSolver(self.board, h_edges=self.h_edges, v_edges=self.v_edges)
        except ValueError:
            return False

        board_copy = [row[:] for row in self.board]
        return solver._propagate(board_copy)

    def check_current_board(self):
        if self._board_valid_now():
            self.status.config(text="Current board is consistent with Tango rules so far.")
        else:
            self.status.config(text="Current board violates Tango constraints.")

    def solve(self):
        try:
            solver = TangoPuzzleSolver(self.board, h_edges=self.h_edges, v_edges=self.v_edges)
            solved = solver.solve(verify_unique=True)
            if solved:
                solved_board = solver.get_solution_board()
                self.solution_cells = {
                    (r, c)
                    for r in range(self.rows)
                    for c in range(self.cols)
                    if (r, c) not in self.fixed_cells and solved_board[r][c] != self.board[r][c]
                }
                self.board = solved_board
                stats = solver.get_stats()
                self._draw_board()
                self.status.config(
                    text=(
                        f"Solved {self.rows}x{self.cols} in {stats['time']:.3f}s, "
                        f"{stats['moves']} search moves."
                    )
                )
            else:
                if solver.solution_count > 1:
                    self.status.config(text="Puzzle has multiple solutions. Add constraints/clues for uniqueness.")
                else:
                    self.status.config(text="No valid solution found for current clues.")
        except Exception as exc:
            messagebox.showerror("Solve Error", str(exc), parent=self.root)


TangoGameUI = TangoUI

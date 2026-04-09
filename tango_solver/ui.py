"""Tkinter UI for Tango puzzle."""

from __future__ import annotations

import colorsys
import json
from pathlib import Path
from typing import List, Optional, Set, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    from PIL import Image
except ImportError:  # pragma: no cover - runtime fallback
    Image = None

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
                "Each row/column must contain exactly half Symbol 1 and half Symbol 2."
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

        self.canvas.create_rectangle(0, 0, board_px_w, board_px_h, outline="#222222", width=2)

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
        setup.geometry("650x560")
        setup.transient(self.root)
        setup.grab_set()

        container = ttk.Frame(setup, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Create Custom Tango Puzzle", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text="Board dimensions must both be even (for example 4x4, 4x6, 6x8). Enter clues with 0=empty, 1=symbol1, 2=symbol2.",
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

        def apply_setup():
            try:
                rows = int(rows_var.get())
                cols = int(cols_var.get())
                if rows < 2 or cols < 2 or rows % 2 != 0 or cols % 2 != 0:
                    raise ValueError("Board dimensions must both be even numbers")
                clues = self._parse_grid_text(clue_text.get("1.0", tk.END), rows, cols)
                self._load_from_data({"rows": rows, "cols": cols, "clues": clues}, source_label="custom setup")
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

    def _estimate_board_shape(self, image, min_size: int = 2, max_size: int = 16) -> Tuple[int, int, Tuple[int, int, int, int], float]:
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

        rough_rows = max(2, detect_peak_count(h_profile) - 1)
        rough_cols = max(2, detect_peak_count(v_profile) - 1)

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

        best_rows = rough_rows if rough_rows in row_lookup else row_scored[0][0]
        best_cols = rough_cols if rough_cols in col_lookup else col_scored[0][0]

        if best_rows in row_lookup:
            best_row_score, (top, bottom) = row_lookup[best_rows]
        else:
            best_row_score, (top, bottom) = row_scored[0][1:3]

        if best_cols in col_lookup:
            best_col_score, (left, right) = col_lookup[best_cols]
        else:
            best_col_score, (left, right) = col_scored[0][1:3]

        second_row_score = row_scored[1][1] if len(row_scored) > 1 else -1e9
        second_col_score = col_scored[1][1] if len(col_scored) > 1 else -1e9
        confidence = 1.0 + min(
            max(0.0, best_row_score - second_row_score) / max(abs(second_row_score), 1.0),
            max(0.0, best_col_score - second_col_score) / max(abs(second_col_score), 1.0),
        )

        return best_rows, best_cols, (left, top, right, bottom), confidence

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
            rows, cols, inner_bounds, confidence = self._estimate_board_shape(cropped)

            if rows % 2 != 0 or cols % 2 != 0:
                raise ValueError("Board dimensions must both be even for Tango")

            use_detected = messagebox.askyesno(
                "Detected Tango Puzzle",
                f"Detected a {rows}x{cols} board with symbol clues (confidence {confidence:.2f}). Use this detection?",
                parent=self.root,
            )
            if not use_detected:
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
                rows, cols = manual_rows, manual_cols
                if rows % 2 != 0 or cols % 2 != 0:
                    raise ValueError("Board dimensions must both be even for Tango")

            clues = self._extract_clues_from_image(cropped, rows, cols, inner_bounds)

            self._load_from_data({"rows": rows, "cols": cols, "clues": clues}, source_label=Path(image_path).name)
            self.status.config(text=f"Imported clues from screenshot ({rows}x{cols}).")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc), parent=self.root)

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

        if rows % 2 != 0 or cols % 2 != 0:
            raise ValueError("Board dimensions must both be even for Tango")
        if len(clues) != rows or any(len(row) != cols for row in clues):
            raise ValueError("Clues grid must match the declared rows and columns")

        for row in clues:
            for value in row:
                if value not in (0, 1, 2):
                    raise ValueError("Clues must contain only 0, 1, or 2")

        self.rows = rows
        self.cols = cols
        self.board = [row[:] for row in clues]
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
            solver = TangoPuzzleSolver(self.board)
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
            solver = TangoPuzzleSolver(self.board)
            solved = solver.solve(verify_unique=False)
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
                self.status.config(text="No valid solution found for current clues.")
        except Exception as exc:
            messagebox.showerror("Solve Error", str(exc), parent=self.root)


TangoGameUI = TangoUI

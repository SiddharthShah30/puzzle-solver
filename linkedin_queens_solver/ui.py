"""Tkinter UI for Queens puzzle."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional, Set, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

try:
    from PIL import Image
except ImportError:  # pragma: no cover - runtime fallback
    Image = None

from .solver import QueensPuzzleSolver


COLOR_PALETTE = {
    0: "#a58dc8",
    1: "#edbe86",
    2: "#8bb9eb",
    3: "#99c78a",
    4: "#b8b8b8",
    5: "#f7785f",
    6: "#c7d96e",
}


class QueensUI:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Queens Solver")
        self.root.geometry("1050x760")

        self.samples_dir = Path(__file__).parent / "samples"

        self.region_map: List[List[int]] = []
        self.size = 0
        self.cell_size = 70

        self.fixed_queens: Set[Tuple[int, int]] = set()
        self.blocked_cells: Set[Tuple[int, int]] = set()
        self.solution_cells: Set[Tuple[int, int]] = set()

        self._setup_ui()
        self.status.config(text="Create a puzzle, load a puzzle JSON, or load the included sample.")

    def _setup_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(outer, text="Queens Puzzle", font=("Helvetica", 16, "bold"))
        title.pack(anchor="w")

        rule_text = (
            "Rules: 1 queen per row, column, and color region. "
            "Queens cannot touch, even diagonally.\n"
            "Click cycle: Empty -> X -> Queen -> Empty"
        )
        self.rule_label = ttk.Label(outer, text=rule_text, font=("Helvetica", 10))
        self.rule_label.pack(anchor="w", pady=(4, 10))

        content = ttk.Frame(outer)
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(content, text="Board", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(left, width=560, height=560, bg="#ffffff")
        self.canvas.pack(padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        right = ttk.LabelFrame(content, text="Controls", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        ttk.Button(right, text="New Puzzle Setup", command=self.new_puzzle_setup).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Import from Screenshot", command=self.import_from_screenshot).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load Example", command=lambda: self.load_sample("linkedin_queens_7x7.json")).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Solve", command=self.solve).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Clear Marks", command=self.clear_marks).pack(fill=tk.X, pady=4)
        ttk.Button(right, text="Load Puzzle JSON", command=self.load_puzzle_json).pack(fill=tk.X, pady=4)

        self.status = ttk.Label(right, text="Ready", wraplength=300)
        self.status.pack(fill=tk.X, pady=(14, 0))

    def _parse_grid_text(self, raw_text: str, size: int) -> List[List[int]]:
        rows = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
        if len(rows) != size:
            raise ValueError(f"Expected {size} rows, found {len(rows)}")

        parsed: List[List[int]] = []
        for line in rows:
            cells = [token for token in line.replace(',', ' ').split(' ') if token]
            if len(cells) != size:
                raise ValueError(f"Each row must have {size} integers")
            parsed.append([int(token) for token in cells])
        return parsed

    def new_puzzle_setup(self):
        setup = tk.Toplevel(self.root)
        setup.title("Queens Puzzle Setup")
        setup.geometry("700x620")
        setup.transient(self.root)
        setup.grab_set()

        container = ttk.Frame(setup, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Create Custom Queens Puzzle", font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(
            container,
            text=(
                "Enter size and region IDs. Rules require exactly N regions with N cells each.\n"
                "Optional fixed queens / blocked cells format: row,col per line (0-based)."
            ),
            wraplength=660,
        ).pack(anchor="w", pady=(6, 10))

        size_row = ttk.Frame(container)
        size_row.pack(fill=tk.X)
        ttk.Label(size_row, text="Board size N:").pack(side=tk.LEFT)
        size_var = tk.StringVar(value="7")
        ttk.Entry(size_row, textvariable=size_var, width=8).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(container, text="Region map (N lines, N integers each):").pack(anchor="w", pady=(12, 4))
        region_text = tk.Text(container, height=14, width=78)
        region_text.pack(fill=tk.BOTH, expand=True)

        default_regions = (
            "0 0 1 1 1 2 2\n"
            "0 1 1 3 1 1 2\n"
            "0 1 3 3 3 1 4\n"
            "0 1 1 3 1 1 4\n"
            "0 5 1 1 1 5 5\n"
            "5 5 5 6 5 5 5\n"
            "5 5 5 5 5 5 5"
        )
        region_text.insert("1.0", default_regions)

        marks_row = ttk.Frame(container)
        marks_row.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        fixed_frame = ttk.Frame(marks_row)
        fixed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(fixed_frame, text="Fixed queens (optional):").pack(anchor="w")
        fixed_text = tk.Text(fixed_frame, height=6, width=35)
        fixed_text.pack(fill=tk.BOTH, expand=True, padx=(0, 6))

        blocked_frame = ttk.Frame(marks_row)
        blocked_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        ttk.Label(blocked_frame, text="Blocked X cells (optional):").pack(anchor="w")
        blocked_text = tk.Text(blocked_frame, height=6, width=35)
        blocked_text.pack(fill=tk.BOTH, expand=True, padx=(6, 0))

        def parse_positions(text_widget: tk.Text) -> Set[Tuple[int, int]]:
            positions: Set[Tuple[int, int]] = set()
            raw = text_widget.get("1.0", tk.END).strip()
            if not raw:
                return positions
            for line in raw.splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) != 2:
                    raise ValueError("Position lines must be in row,col format")
                positions.add((int(parts[0]), int(parts[1])))
            return positions

        def apply_setup():
            try:
                size = int(size_var.get())
                regions = self._parse_grid_text(region_text.get("1.0", tk.END), size)
                fixed = parse_positions(fixed_text)
                blocked = parse_positions(blocked_text)

                data = {
                    "regions": regions,
                    "fixed_queens": sorted(list(fixed)),
                    "blocked": sorted(list(blocked)),
                }
                self._load_from_data(data, source_label="custom setup")
                setup.destroy()
            except Exception as exc:
                messagebox.showerror("Invalid Puzzle", str(exc), parent=setup)

        button_row = ttk.Frame(container)
        button_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_row, text="Apply Puzzle", command=apply_setup).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Cancel", command=setup.destroy).pack(side=tk.LEFT, padx=(8, 0))

    def import_from_screenshot(self):
        """Create a puzzle from a screenshot by color-clustering cell centers."""
        if Image is None:
            messagebox.showerror(
                "Missing Dependency",
                "Pillow is required for screenshot import. Install it with: pip install pillow",
            )
            return

        image_path = filedialog.askopenfilename(
            title="Select Queens Screenshot",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp")],
        )
        if not image_path:
            return

        try:
            image = Image.open(image_path).convert("RGB")

            bounds = self._find_content_bounds(image)
            cropped = image.crop(bounds)
            size, confidence = self._estimate_grid_size(cropped)

            use_detected = messagebox.askyesno(
                "Detected Board Size",
                f"Detected board size: {size}x{size} (confidence {confidence:.2f}).\nUse this size?",
                parent=self.root,
            )
            if not use_detected:
                manual_size = simpledialog.askinteger(
                    "Board Size",
                    "Enter board size N manually:",
                    minvalue=1,
                    parent=self.root,
                )
                if manual_size is None:
                    return
                size = manual_size

            regions = self._regions_from_image(cropped, size)
            self._load_from_data({"regions": regions, "fixed_queens": [], "blocked": []}, source_label=Path(image_path).name)
            self.status.config(text=f"Imported regions from screenshot ({size}x{size}). Add X/Queens and solve.")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))

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

    def _estimate_grid_size(self, image, min_size: int = 4, max_size: int = 14) -> Tuple[int, float]:
        """Estimate board size by matching candidate grid lines to edge profiles.

        This uses line-vs-gap contrast with offset search, which is more robust than
        sampling only internal lines and avoids common harmonic mistakes (for example,
        detecting 8x8 as 4x4).
        """
        width, height = image.size
        if width < 20 or height < 20:
            raise ValueError("Image is too small to detect a puzzle grid")

        # Downscale very large images for faster scoring.
        max_dim = 900
        if max(width, height) > max_dim:
            scale = max_dim / float(max(width, height))
            new_size = (max(20, int(width * scale)), max(20, int(height * scale)))
            image = image.resize(new_size)
            width, height = image.size

        gray = image.convert("L")
        px = gray.load()

        vertical_profile = [0.0 for _ in range(width)]
        horizontal_profile = [0.0 for _ in range(height)]

        for x in range(1, width):
            total = 0.0
            for y in range(height):
                total += abs(int(px[x, y]) - int(px[x - 1, y]))
            vertical_profile[x] = total / height

        for y in range(1, height):
            total = 0.0
            for x in range(width):
                total += abs(int(px[x, y]) - int(px[x, y - 1]))
            horizontal_profile[y] = total / width

        def smooth_profile(values: List[float], radius: int = 2) -> List[float]:
            if len(values) <= 2 or radius <= 0:
                return values[:]

            prefix = [0.0]
            running = 0.0
            for value in values:
                running += value
                prefix.append(running)

            out = [0.0 for _ in values]
            last = len(values) - 1
            for idx in range(len(values)):
                left = max(0, idx - radius)
                right = min(last, idx + radius)
                out[idx] = (prefix[right + 1] - prefix[left]) / (right - left + 1)
            return out

        vertical_profile = smooth_profile(vertical_profile, radius=2)
        horizontal_profile = smooth_profile(horizontal_profile, radius=2)

        def detect_peak_count(profile: List[float]) -> int:
            if len(profile) < 5:
                return 0

            p_min = min(profile)
            p_max = max(profile)
            if p_max <= p_min:
                return 0

            threshold = p_min + 0.55 * (p_max - p_min)
            candidates = [
                idx
                for idx in range(1, len(profile) - 1)
                if profile[idx] >= threshold and profile[idx] >= profile[idx - 1] and profile[idx] >= profile[idx + 1]
            ]

            if not candidates:
                threshold = p_min + 0.40 * (p_max - p_min)
                candidates = [
                    idx
                    for idx in range(1, len(profile) - 1)
                    if profile[idx] >= threshold and profile[idx] >= profile[idx - 1] and profile[idx] >= profile[idx + 1]
                ]

            min_sep = max(2, int(len(profile) / (max_size * 2.2)))
            selected: List[int] = []
            for idx in sorted(candidates, key=lambda i: profile[i], reverse=True):
                if all(abs(idx - prev) >= min_sep for prev in selected):
                    selected.append(idx)

            return len(selected)

        peak_count_x = detect_peak_count(vertical_profile)
        peak_count_y = detect_peak_count(horizontal_profile)
        rough_size = int(round(((peak_count_x + peak_count_y) / 2.0) - 1.0))
        rough_size = min(max(2, rough_size), max_size)

        def mean_at_indices(profile: List[float], indices: List[int]) -> float:
            if not indices:
                return 0.0
            return sum(profile[idx] for idx in indices) / float(len(indices))

        def estimate_borders(profile: List[float], length: int) -> Tuple[int, int]:
            zone = max(5, int(length * 0.20))
            left_zone = profile[1:zone]
            right_zone = profile[max(1, length - zone): length - 1]

            if not left_zone or not right_zone:
                return 1, max(2, length - 1)

            left = 1 + max(range(len(left_zone)), key=lambda i: left_zone[i])
            right_start = max(1, length - zone)
            right = right_start + max(range(len(right_zone)), key=lambda i: right_zone[i])

            if right - left < int(length * 0.45):
                return 1, max(2, length - 1)
            return left, right

        def axis_score(profile: List[float], length: int, size: int) -> float:
            if size <= 1:
                return -1e9

            border_left, border_right = estimate_borders(profile, length)
            span = float(max(2, border_right - border_left))
            step = span / float(size)
            if step < 3.0:
                return -1e9

            # Small local jitter keeps scoring stable if border detection is off by 1-2 px.
            best = -1e9
            for jitter in (-2, -1, 0, 1, 2):
                line_indices: List[int] = []
                gap_indices: List[int] = []

                for i in range(size + 1):
                    pos = int(round(border_left + jitter + i * step))
                    pos = min(max(1, pos), length - 1)
                    line_indices.append(pos)

                for i in range(size):
                    mid = int(round(border_left + jitter + (i + 0.5) * step))
                    mid = min(max(1, mid), length - 1)
                    gap_indices.append(mid)

                line_strength = mean_at_indices(profile, line_indices)
                gap_strength = mean_at_indices(profile, gap_indices)

                # High score when predicted lines hit strong edges but gaps stay quiet.
                score = (line_strength - 0.80 * gap_strength) + 0.20 * line_strength
                if score > best:
                    best = score

            return best

        min_size = max(2, min_size)
        max_size = max(min_size, max_size)

        scored: List[Tuple[int, float]] = []
        for n in range(min_size, max_size + 1):
            v_score = axis_score(vertical_profile, width, n)
            h_score = axis_score(horizontal_profile, height, n)
            size_penalty = 0.06 * abs(n - rough_size)
            scored.append((n, ((v_score + h_score) / 2.0) - size_penalty))

        scored.sort(key=lambda item: item[1], reverse=True)
        best_n, best_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else -1e9
        spread = max(best_score - second_score, 0.0)
        baseline = max(abs(second_score), 1.0)
        confidence = 1.0 + (spread / baseline)
        return best_n, confidence

    def _regions_from_image(self, image, size: int) -> List[List[int]]:
        width, height = image.size
        cell_w = width / size
        cell_h = height / size

        sampled: List[List[Tuple[int, int, int]]] = []
        for r in range(size):
            row_colors = []
            for c in range(size):
                x = min(width - 1, max(0, int((c + 0.5) * cell_w)))
                y = min(height - 1, max(0, int((r + 0.5) * cell_h)))
                row_colors.append(image.getpixel((x, y)))
            sampled.append(row_colors)

        # Cluster similar colors into region ids.
        threshold = 38.0
        centroids: List[Tuple[float, float, float]] = []
        counts: List[int] = []
        region_map = [[-1 for _ in range(size)] for _ in range(size)]

        def color_distance(a: Tuple[int, int, int], b: Tuple[float, float, float]) -> float:
            return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

        for r in range(size):
            for c in range(size):
                color = sampled[r][c]
                if not centroids:
                    centroids.append((float(color[0]), float(color[1]), float(color[2])))
                    counts.append(1)
                    region_map[r][c] = 0
                    continue

                best_idx = min(range(len(centroids)), key=lambda i: color_distance(color, centroids[i]))
                best_dist = color_distance(color, centroids[best_idx])

                if best_dist <= threshold:
                    region_map[r][c] = best_idx
                    old_count = counts[best_idx]
                    cx, cy, cz = centroids[best_idx]
                    centroids[best_idx] = (
                        (cx * old_count + color[0]) / (old_count + 1),
                        (cy * old_count + color[1]) / (old_count + 1),
                        (cz * old_count + color[2]) / (old_count + 1),
                    )
                    counts[best_idx] = old_count + 1
                else:
                    centroids.append((float(color[0]), float(color[1]), float(color[2])))
                    counts.append(1)
                    region_map[r][c] = len(centroids) - 1

        # If colors over-segment due to anti-aliasing, merge closest clusters until <= size.
        while len(centroids) > size:
            best_pair = None
            best_dist = float("inf")
            for i in range(len(centroids)):
                for j in range(i + 1, len(centroids)):
                    d = color_distance((int(centroids[i][0]), int(centroids[i][1]), int(centroids[i][2])), centroids[j])
                    if d < best_dist:
                        best_dist = d
                        best_pair = (i, j)

            if best_pair is None:
                break

            i, j = best_pair
            total = counts[i] + counts[j]
            centroids[i] = (
                (centroids[i][0] * counts[i] + centroids[j][0] * counts[j]) / total,
                (centroids[i][1] * counts[i] + centroids[j][1] * counts[j]) / total,
                (centroids[i][2] * counts[i] + centroids[j][2] * counts[j]) / total,
            )
            counts[i] = total

            for r in range(size):
                for c in range(size):
                    if region_map[r][c] == j:
                        region_map[r][c] = i
                    elif region_map[r][c] > j:
                        region_map[r][c] -= 1

            del centroids[j]
            del counts[j]

        # Re-label to contiguous 0..k-1
        remap = {}
        next_id = 0
        for r in range(size):
            for c in range(size):
                rid = region_map[r][c]
                if rid not in remap:
                    remap[rid] = next_id
                    next_id += 1
                region_map[r][c] = remap[rid]

        return region_map

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

    def _load_from_file(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._load_from_data(data, source_label=path.name)

    def _load_from_data(self, data: dict, source_label: str):
        if "regions" not in data:
            raise ValueError("Puzzle JSON must include a 'regions' grid")

        self.region_map = data["regions"]
        self.size = len(self.region_map)
        if self.size == 0 or any(len(row) != self.size for row in self.region_map):
            raise ValueError("Regions grid must be square")

        self.fixed_queens = set(tuple(pos) for pos in data.get("fixed_queens", []))
        self.blocked_cells = set(tuple(pos) for pos in data.get("blocked", []))
        self.solution_cells = set()

        self.cell_size = max(40, min(78, 560 // self.size))
        self._draw_board()
        self.status.config(text=f"Loaded {source_label} ({self.size}x{self.size})")

    def _draw_board(self):
        self.canvas.delete("all")
        board_pixels = self.cell_size * self.size
        self.canvas.config(width=board_pixels, height=board_pixels)

        for r in range(self.size):
            for c in range(self.size):
                x1 = c * self.cell_size
                y1 = r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                rid = self.region_map[r][c]
                fill = COLOR_PALETTE.get(rid, "#dddddd")
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="#242424", width=1)

                if (r, c) in self.blocked_cells:
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text="X",
                        fill="#2d2d2d",
                        font=("Helvetica", max(12, self.cell_size // 3), "bold"),
                    )
                if (r, c) in self.fixed_queens:
                    self.canvas.create_text(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        text="♛",
                        fill="#111111",
                        font=("Helvetica", max(14, self.cell_size // 2), "bold"),
                    )
                if (r, c) in self.solution_cells:
                    self.canvas.create_oval(x1 + 4, y1 + 4, x2 - 4, y2 - 4, outline="#0b5ed7", width=2)

    def on_canvas_click(self, event):
        if self.size == 0:
            return

        col = event.x // self.cell_size
        row = event.y // self.cell_size

        if not (0 <= row < self.size and 0 <= col < self.size):
            return

        cell = (row, col)
        self.solution_cells.clear()

        # Tap cycle: empty -> X -> queen -> empty
        if cell in self.fixed_queens:
            self.fixed_queens.remove(cell)
        elif cell in self.blocked_cells:
            self.blocked_cells.remove(cell)
            self.fixed_queens.add(cell)
        else:
            self.blocked_cells.add(cell)

        # queen and X cannot coexist
        if cell in self.fixed_queens and cell in self.blocked_cells:
            self.blocked_cells.remove(cell)

        self._draw_board()

    def clear_marks(self):
        self.fixed_queens.clear()
        self.blocked_cells.clear()
        self.solution_cells.clear()
        self._draw_board()
        self.status.config(text="Cleared all marks")

    def solve(self):
        try:
            solver = QueensPuzzleSolver(
                region_map=self.region_map,
                fixed_queens=list(self.fixed_queens),
                blocked_cells=set(self.blocked_cells),
            )
            if solver.solve():
                sol = solver.get_solution_board()
                self.solution_cells = {
                    (r, c)
                    for r in range(self.size)
                    for c in range(self.size)
                    if sol[r][c] == 1
                }
                self.fixed_queens = set(self.solution_cells)
                self.blocked_cells = {
                    (r, c)
                    for r in range(self.size)
                    for c in range(self.size)
                    if (r, c) not in self.fixed_queens
                }
                stats = solver.get_stats()
                self.status.config(text=f"Solved in {stats['time']:.4f}s with {stats['moves']} placements")
            else:
                self.status.config(text="No valid solution for current marks")
                messagebox.showwarning("No Solution", "No valid arrangement fits the current X/Queen marks.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

        self._draw_board()


# Backward compatibility with previous imports.
LinkedInQueensUI = QueensUI

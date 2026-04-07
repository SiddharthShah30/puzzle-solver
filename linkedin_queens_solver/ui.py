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
            size, confidence = self._estimate_grid_size(image)

            if confidence < 1.08:
                manual_size = simpledialog.askinteger(
                    "Board Size",
                    "Could not confidently detect board size. Enter N manually:",
                    minvalue=1,
                    parent=self.root,
                )
                if manual_size is None:
                    return
                size = manual_size
            else:
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

            regions = self._regions_from_image(image, size)
            self._load_from_data({"regions": regions, "fixed_queens": [], "blocked": []}, source_label=Path(image_path).name)
            self.status.config(text=f"Imported regions from screenshot ({size}x{size}). Add X/Queens and solve.")
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))

    def _estimate_grid_size(self, image: "Image.Image", min_size: int = 4, max_size: int = 14) -> Tuple[int, float]:
        """Estimate board size by scoring edge strength on candidate grid lines."""
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

        def vertical_edge_at(x: int) -> float:
            x = min(max(1, x), width - 1)
            total = 0.0
            for y in range(height):
                total += abs(int(px[x, y]) - int(px[x - 1, y]))
            return total / height

        def horizontal_edge_at(y: int) -> float:
            y = min(max(1, y), height - 1)
            total = 0.0
            for x in range(width):
                total += abs(int(px[x, y]) - int(px[x, y - 1]))
            return total / width

        min_size = max(2, min_size)
        max_size = max(min_size, max_size)

        scored: List[Tuple[int, float]] = []
        for n in range(min_size, max_size + 1):
            v_score = 0.0
            h_score = 0.0

            for i in range(1, n):
                x = int(round(i * width / n))
                y = int(round(i * height / n))
                v_score += vertical_edge_at(x)
                h_score += horizontal_edge_at(y)

            avg_score = (v_score + h_score) / max(1, 2 * (n - 1))
            scored.append((n, avg_score))

        scored.sort(key=lambda item: item[1], reverse=True)
        best_n, best_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else 1e-9
        confidence = best_score / max(second_score, 1e-9)
        return best_n, confidence

    def _regions_from_image(self, image: "Image.Image", size: int) -> List[List[int]]:
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
            defaultdir=self.samples_dir,
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

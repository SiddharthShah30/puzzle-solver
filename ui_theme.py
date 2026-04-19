"""Shared UI theme helpers for the puzzle app."""

from __future__ import annotations

from typing import Dict
import tkinter as tk
from tkinter import ttk


THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "name": "light",
        "bg": "#eef2f7",
        "panel": "#ffffff",
        "panel_alt": "#f7f9fc",
        "canvas": "#ffffff",
        "text": "#17212b",
        "muted": "#5e6a78",
        "accent": "#2563eb",
        "accent_soft": "#dbeafe",
        "border": "#d4dbe6",
        "shadow": "#c8d0dd",
        "button_bg": "#f5f7fb",
        "button_fg": "#17212b",
        "button_active": "#e5ecf8",
        "input_bg": "#ffffff",
        "input_fg": "#17212b",
        "selection": "#dbeafe",
        "header": "#0f172a",
    },
    "dark": {
        "name": "dark",
        "bg": "#0f172a",
        "panel": "#111c30",
        "panel_alt": "#17233b",
        "canvas": "#0b1220",
        "text": "#e5eef9",
        "muted": "#a7b3c6",
        "accent": "#60a5fa",
        "accent_soft": "#1d4ed8",
        "border": "#2a3b57",
        "shadow": "#0a1020",
        "button_bg": "#1b2740",
        "button_fg": "#e5eef9",
        "button_active": "#243553",
        "input_bg": "#0f172a",
        "input_fg": "#e5eef9",
        "selection": "#1d4ed8",
        "header": "#f8fafc",
    },
}


def get_theme(theme_name: str) -> Dict[str, str]:
    return THEMES.get(theme_name, THEMES["light"])


def apply_app_theme(root: tk.Misc, theme_name: str = "light") -> Dict[str, str]:
    theme = get_theme(theme_name)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=theme["bg"], foreground=theme["text"], font=("Segoe UI", 10))
    style.configure("TFrame", background=theme["bg"])
    style.configure("TLabel", background=theme["bg"], foreground=theme["text"])
    style.configure("TButton", padding=(10, 6), background=theme["button_bg"], foreground=theme["button_fg"])
    style.map(
        "TButton",
        background=[("active", theme["button_active"]), ("pressed", theme["accent_soft"])],
        foreground=[("disabled", theme["muted"])],
    )
    style.configure("TEntry", fieldbackground=theme["input_bg"], foreground=theme["input_fg"])
    style.configure("TText", fieldbackground=theme["input_bg"], foreground=theme["input_fg"])
    style.configure("TLabelframe", background=theme["bg"], bordercolor=theme["border"])
    style.configure("TLabelframe.Label", background=theme["bg"], foreground=theme["text"], font=("Segoe UI", 10, "bold"))
    style.configure("TSeparator", background=theme["border"])

    if hasattr(root, "configure"):
        try:
            root.configure(bg=theme["bg"])
        except tk.TclError:
            pass
    return theme
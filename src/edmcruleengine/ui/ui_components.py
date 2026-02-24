"""
Shared tkinter UI components and button styles for EDMC VKB Connector.
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Any, Callable, Optional

# Canvas-drawn icon button size
ICON_BUTTON_SIZE = 20

BUTTON_PALETTES = {
    "default": {"bg": "#95a5a6", "fg": "white"},
    "info": {"bg": "#3498db", "fg": "white"},
    "success": {"bg": "#27ae60", "fg": "white"},
    "danger": {"bg": "#e74c3c", "fg": "white"},
    "edit": {"bg": "#3498db", "fg": "white"},
    "add": {"bg": "#27ae60", "fg": "white"},
    "up": {"bg": "#3498db", "fg": "white"},
    "down": {"bg": "#3498db", "fg": "white"},
    "duplicate": {"bg": "#8e44ad", "fg": "white"},
    "delete": {"bg": "#e74c3c", "fg": "white"},
}


def get_button_palette(style: str) -> dict[str, str]:
    """Return a color palette by style key."""
    return BUTTON_PALETTES.get(style, BUTTON_PALETTES["default"])


class ToolTip:
    """Simple tooltip helper for tkinter widgets."""

    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip_window = None

        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self._tip_window, text=self.text, relief="solid", borderwidth=1)
        label.pack(ipadx=6, ipady=3)

    def _hide(self, event=None) -> None:
        self._cancel()
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None


class TwoStateCheckbutton(tk.Canvas):
    """A 2-state checkbox widget with OFF (empty) and ON (checkmark)."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str = "",
        variable: Optional[tk.BooleanVar] = None,
        command: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, width=20, height=20, highlightthickness=0, bg="white", **kwargs)
        self.text = text
        self.variable = variable if variable else tk.BooleanVar(value=False)
        self.command = command
        self.label_font = ("TkDefaultFont", 10)

        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _on_click(self, event=None) -> None:
        self.variable.set(not self.variable.get())
        self._draw()
        if self.command:
            self.command()

    def _draw(self) -> None:
        self.delete("all")
        is_checked = self.variable.get()

        box_color = "#333"
        if is_checked:
            box_fill = "#27ae60"
            symbol = "✓"
            symbol_color = "white"
        else:
            box_fill = "white"
            symbol = ""
            symbol_color = "#333"

        self.create_rectangle(2, 2, 16, 16, fill=box_fill, outline=box_color, width=1)
        if symbol:
            self.create_text(9, 9, text=symbol, font=self.label_font, fill=symbol_color)
        if self.text:
            self.create_text(22, 9, text=self.text, anchor="w", font=self.label_font)


class IconButton(tk.Canvas):
    """A small canvas-drawn colored icon button.

    Draws crisp vector icons that render identically across platforms
    without relying on emoji font support.
    """

    PALETTES = {
        "edit": {"bg": "#3498db", "fg": "white", "hover": "#2980b9", "eraser": "#f39c12"},
        "delete": {"bg": "#e74c3c", "fg": "white", "hover": "#c0392b"},
        "add": {"bg": "#27ae60", "fg": "white", "hover": "#1e8449"},
        "up": {"bg": "#3498db", "fg": "white", "hover": "#2980b9"},
        "down": {"bg": "#3498db", "fg": "white", "hover": "#2980b9"},
        "duplicate": {"bg": "#8e44ad", "fg": "white", "hover": "#6c3483"},
    }

    def __init__(self, parent, icon_type: str, command=None, size=ICON_BUTTON_SIZE, tooltip: str = "", **kw):
        super().__init__(parent, width=size, height=size, highlightthickness=0, bd=0, **kw)
        self._icon_type = icon_type
        self._command = command
        self._size = size
        self._palette = self.PALETTES.get(icon_type, {"bg": "#95a5a6", "fg": "white", "hover": "#7f8c8d"})
        self._hovering = False

        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        if tooltip:
            self._tooltip = tooltip
            self.bind("<Enter>", self._show_tip, add="+")
            self.bind("<Leave>", self._hide_tip, add="+")
            self._tip_window = None

    def _draw(self):
        self.delete("all")
        s = self._size
        bg = self._palette["hover"] if self._hovering else self._palette["bg"]
        fg = self._palette["fg"]

        # Rounded-rect background
        r = 3
        self.create_rectangle(r, r, s - r, s - r, fill=bg, outline="", width=0)
        self.create_rectangle(0, r, s, s - r, fill=bg, outline="")
        self.create_rectangle(r, 0, s - r, s, fill=bg, outline="")
        for cx, cy in [(r, r), (s - r, r), (r, s - r), (s - r, s - r)]:
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=bg, outline="")

        m = s // 2
        p = 5

        if self._icon_type == "edit":
            # Pencil icon: angled body, triangular tip, eraser end
            angle = math.radians(45)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            half_w = 2.0          # half-width of the pencil shaft
            shaft_len = s - p * 2 - 3
            # Centre the pencil diagonally across the canvas
            cx, cy = s / 2, s / 2
            # Unit vectors along and across the pencil axis (bottom-left to top-right)
            ax, ay = cos_a, -sin_a   # along axis
            nx, ny = sin_a,  cos_a   # normal (perpendicular)
            # Four corners of shaft rectangle
            tip_end   = shaft_len * 0.35
            eraser_end = shaft_len * 0.5
            def pt(along, across):
                return (cx + ax * along + nx * across,
                        cy + ay * along + ny * across)
            # Eraser end (flat cap)
            e1 = pt(-eraser_end,  half_w)
            e2 = pt(-eraser_end, -half_w)
            # Shaft corners near tip
            s1 = pt( tip_end,  half_w)
            s2 = pt( tip_end, -half_w)
            # Pencil tip point
            tip = pt(tip_end + half_w + 2, 0)
            # Draw shaft
            self.create_polygon(e1[0], e1[1], e2[0], e2[1],
                                s2[0], s2[1], s1[0], s1[1],
                                fill=fg, outline="")
            # Draw tip triangle
            self.create_polygon(s1[0], s1[1], s2[0], s2[1],
                                tip[0], tip[1],
                                fill=fg, outline="")
            # Eraser band (contrasting rect across the flat end)
            e3 = pt(-eraser_end + 3,  half_w)
            e4 = pt(-eraser_end + 3, -half_w)
            eraser_color = self._palette.get("eraser", "#e88")
            self.create_polygon(e1[0], e1[1], e2[0], e2[1],
                                e4[0], e4[1], e3[0], e3[1],
                                fill=eraser_color, outline="")
        elif self._icon_type == "delete":
            self.create_line(p, p, s - p, s - p, fill=fg, width=2)
            self.create_line(s - p, p, p, s - p, fill=fg, width=2)
        elif self._icon_type == "add":
            self.create_line(m, p, m, s - p, fill=fg, width=2)
            self.create_line(p, m, s - p, m, fill=fg, width=2)
        elif self._icon_type == "up":
            self.create_polygon(m, p, s - p, s - p, p, s - p, fill=fg, outline="")
        elif self._icon_type == "down":
            self.create_polygon(m, s - p, s - p, p, p, p, fill=fg, outline="")
        elif self._icon_type == "duplicate":
            off = 3
            self.create_rectangle(p + off, p, s - p, s - p - off, outline=fg, width=1.5, fill="")
            self.create_rectangle(p, p + off, s - p - off, s - p, outline=fg, width=1.5, fill="")

    def _on_click(self, event=None):
        if self._command:
            self._command()

    def _on_enter(self, event=None):
        self._hovering = True
        self._draw()

    def _on_leave(self, event=None):
        self._hovering = False
        self._draw()

    def _show_tip(self, event=None):
        if self._tip_window:
            return
        x = self.winfo_rootx() + self._size + 2
        y = self.winfo_rooty()
        tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=getattr(self, "_tooltip", ""), bg="#333", fg="white",
                 font=("TkDefaultFont", 8), padx=4, pady=2).pack()
        self._tip_window = tw

    def _hide_tip(self, event=None):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


def apply_colored_button_style(button: tk.Button, style: str) -> None:
    """Apply a shared color palette to an existing tk.Button."""
    palette = get_button_palette(style)
    button.configure(
        bg=palette["bg"],
        fg=palette["fg"],
        activebackground=palette["bg"],
        activeforeground=palette["fg"],
    )


def create_icon_action_button(
    parent: tk.Misc,
    *,
    action: str,
    command: Optional[Callable[..., Any]] = None,
    tooltip_text: str = "",
    size: int = ICON_BUTTON_SIZE,
    **kwargs: Any,
) -> IconButton:
    """Create a small action icon button using the shared canvas icon style."""
    return IconButton(parent, action, command=command, size=size, tooltip=tooltip_text, **kwargs)


def create_colored_button(
    parent: tk.Misc,
    *,
    text: Optional[str] = None,
    textvariable: Optional[tk.Variable] = None,
    command: Optional[Callable[..., Any]] = None,
    style: str = "default",
    tooltip_text: str = "",
    font: Any = ("TkDefaultFont", 9),
    padx: int = 6,
    pady: int = 4,
    width: Optional[int] = None,
    height: Optional[int] = None,
    relief: str = tk.RAISED,
    bd: int = 1,
    **kwargs: Any,
) -> tk.Button:
    """Create a tk.Button with shared color styles and optional tooltip."""
    palette = get_button_palette(style)
    options: dict[str, Any] = {
        "command": command,
        "bg": palette["bg"],
        "fg": palette["fg"],
        "padx": padx,
        "pady": pady,
        "font": font,
        "relief": relief,
        "bd": bd,
        "activebackground": palette["bg"],
        "activeforeground": palette["fg"],
    }
    if text is not None:
        options["text"] = text
    if textvariable is not None:
        options["textvariable"] = textvariable
    if width is not None:
        options["width"] = width
    if height is not None:
        options["height"] = height
    options.update(kwargs)

    button = tk.Button(parent, **options)
    if tooltip_text:
        ToolTip(button, tooltip_text)
    return button


__all__ = [
    "apply_colored_button_style",
    "create_icon_action_button",
    "ICON_BUTTON_SIZE",
    "IconButton",
    "ToolTip",
    "TwoStateCheckbutton",
    "create_colored_button",
    "get_button_palette",
]

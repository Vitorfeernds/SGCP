import os, json, tkinter as tk
from app.config import DATA_DIR

# ============================================================================
# SISTEMA DE TEMAS
# ============================================================================
_LIGHT = {
    "green":       "#16A34A", "green_dark":  "#15803D", "green_light": "#DCFCE7",
    "dark":        "#111827", "dark_soft":   "#1F2937", "gray":        "#6B7280",
    "gray_light":  "#E5E7EB", "bg":          "#F3F4F6", "card":        "#FFFFFF",
    "white":       "#FFFFFF", "amber":       "#F59E0B", "amber_light": "#FEF3C7",
    "blue":        "#2563EB", "blue_light":  "#DBEAFE", "red":         "#DC2626",
    "red_light":   "#FEE2E2", "purple":      "#7C3AED", "purple_light":"#EDE9FE",
    "text":        "#070B14", "subtext":     "#424750",
}
_DARK = {
    "green":       "#22C55E", "green_dark":  "#16A34A", "green_light": "#14532D",
    "dark":        "#02091A", "dark_soft":   "#334155", "gray":        "#94A3B8",
    "gray_light":  "#334155", "bg":          "#142141", "card":        "#1E293B",
    "white":       "#FFFFFF", "amber":       "#FBBF24", "amber_light": "#2D1A00",
    "blue":        "#60A5FA", "blue_light":  "#1E3A8A", "red":         "#E22828",
    "red_light":   "#4C0519", "purple":      "#A78BFA", "purple_light":"#2E1065",
    "text":        "#D9E2EB", "subtext":     "#C0CAD8",
}

CURRENT_THEME = "light"
COLORS = dict(_LIGHT)

_THEME_FILE = os.path.join(DATA_DIR if "DATA_DIR" in dir() else "data", "theme.json")


# ============================================================================
# PALETA / FONTE / STATUS
# ============================================================================
FONT = "Segoe UI"

STATUS_CORES = {
    "Em preparo": (COLORS["amber"], COLORS["amber_light"]),
    "Finalizado": (COLORS["green"], COLORS["green_light"]),
    "Aguardando": (COLORS["blue"],  COLORS["blue_light"]),
    "Cancelado":  (COLORS["red"],   COLORS["red_light"]),
}


def set_theme(name: str) -> None:
    global CURRENT_THEME

    CURRENT_THEME = name
    COLORS.update(_LIGHT if name == "light" else _DARK)

    try:
        os.makedirs(os.path.dirname(_THEME_FILE), exist_ok=True)

        with open(_THEME_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"theme": name},
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception:
        pass


def load_theme() -> None:
    try:
        with open(_THEME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        set_theme(data.get("theme", "light"))

    except Exception:
        set_theme("light")

# ── helpers de interpolação de cor ─────────────────────────────────────────
def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _rgb_to_hex(r, g, b) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

def _lerp_color(c1: str, c2: str, t: float) -> str:
    r1,g1,b1 = _hex_to_rgb(c1)
    r2,g2,b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))

# ============================================================================
# HELPERS DE UI
# ============================================================================
def brl(v):
    return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")


class HoverButton(tk.Label):
    """Botão com transição suave de cor via interpolação linear."""
    _STEPS = 8      # frames da animação
    _DELAY = 14     # ms entre frames (~70fps)

    def __init__(self, master, text, command=None,
                 bg=None, fg=None, hover_bg=None,
                 font_size=11, bold=True, padx=16, pady=10, **kw):
        # Defaults resolvidos em runtime (respeitam troca de tema)
        bg       = bg       or COLORS["green"]
        fg       = fg       or COLORS["white"]
        hover_bg = hover_bg or COLORS["green_dark"]
        w = "bold" if bold else "normal"
        super().__init__(master, text=text, bg=bg, fg=fg,
                         font=(FONT, font_size, w), cursor="hand2",
                         padx=padx, pady=pady, **kw)
        self._bg    = bg
        self._hover = hover_bg
        self._cmd   = command
        self._anim  = None
        self._step  = 0

        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _=None):
        self._animate_to(self._hover)

    def _on_leave(self, _=None):
        self._animate_to(self._bg)

    def _on_click(self, _=None):
        if self._cmd:
            self._cmd()

    def _animate_to(self, target: str):
        if self._anim:
            try: self.after_cancel(self._anim)
            except Exception: pass
        try:
            current = self.cget("bg")
        except Exception:
            current = self._bg
        self._do_step(current, target, 1)

    def _do_step(self, start: str, end: str, step: int):
        if not self.winfo_exists():
            return
        t = step / self._STEPS
        try:
            self.config(bg=_lerp_color(start, end, t))
        except Exception:
            return
        if step < self._STEPS:
            self._anim = self.after(self._DELAY,
                                    lambda: self._do_step(start, end, step + 1))
        else:
            try: self.config(bg=end)
            except Exception: pass

import re
import tkinter as tk
from tkinter import ttk, messagebox
import platform
from app.theme import COLORS, FONT, HoverButton, set_theme, CURRENT_THEME

class BaseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("S.G.C.P - Sistema de Gestao e Controle de Pedidos")
        self.configure(bg=COLORS["bg"])

        # Tela cheia imediata (cross-platform)
        try:
            if platform.system() == "Windows":
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            self.geometry("1200x800")
        self.minsize(900, 600)

        self._tick()

    def navegar(self, tela):
        if self.tela_atual == tela:
            return
        self.tela_atual = tela
        self._render_tela(tela)

    def _montar_layout(self, titulo, subtitulo):
        root = tk.Frame(self.container, bg=COLORS["bg"])
        root.pack(fill="both", expand=True)

        # ── Header ───────────────────────────────────────────────────────────
        header = tk.Frame(root, bg=COLORS["dark"], height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        htext = tk.Frame(header, bg=COLORS["dark"])
        htext.pack(side="left", padx=20)
        tk.Label(htext, text=titulo, bg=COLORS["dark"], fg=COLORS["white"],
                 font=(FONT, 17, "bold")).pack(anchor="w", pady=(14, 0))
        tk.Label(htext, text=subtitulo, bg=COLORS["dark"], fg=COLORS["green"],
                 font=(FONT, 9)).pack(anchor="w")

        # Botão de tema (lua/sol)
        tema_icon = "☀" if CURRENT_THEME == "dark" else "☾"
        def _toggle_tema():
            set_theme("light" if CURRENT_THEME == "dark" else "dark")
            self.limpar_container()
            if   self.tela_atual == "home":     self.mostrar_dashboard()
            elif self.tela_atual == "pedidos":  self.mostrar_pedidos()
            elif self.tela_atual == "cardapio": self.mostrar_cardapio()
        HoverButton(header, tema_icon, command=_toggle_tema,
                    bg=COLORS["dark_soft"], hover_bg=COLORS["gray"],
                    font_size=15, bold=False, padx=10, pady=6).pack(
                        side="right", padx=(0, 6))
        HoverButton(header, "Sair", command=self._logout,
                    bg=COLORS["dark_soft"], hover_bg=COLORS["red"],
                    font_size=9, padx=12, pady=6).pack(side="right", padx=(18, 0))

        # ── Corpo com scroll ─────────────────────────────────────────────────
        wrap = tk.Frame(root, bg=COLORS["bg"])
        wrap.pack(fill="both", expand=True)
        cv = tk.Canvas(wrap, bg=COLORS["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        sf = tk.Frame(cv, bg=COLORS["bg"])
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        wid = cv.create_window((0, 0), window=sf, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfig(wid, width=e.width))
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Scroll localizado — só age quando o mouse está sobre este canvas
        def _on_wheel(event):
            cv.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_scroll(e):
            cv.bind_all("<MouseWheel>", _on_wheel)
        def _unbind_scroll(e):
            cv.unbind_all("<MouseWheel>")
        cv.bind("<Enter>", _bind_scroll)
        cv.bind("<Leave>", _unbind_scroll)
        # Linux
        cv.bind("<Button-4>", lambda e: cv.yview_scroll(-1, "units"))
        cv.bind("<Button-5>", lambda e: cv.yview_scroll(1, "units"))

        self._montar_menu_inferior(root)
        return sf
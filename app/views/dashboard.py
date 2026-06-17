import tkinter as tk
from app.logic.analytics import _calcular_fluxo
from app.theme import COLORS, FONT, HoverButton, brl
from app.config import TOTAL_MESAS
from app.logic.analytics import mesas_ocupadas, _calcular_vendas
from app.db.usuarios import MONGO_OK
from datetime import datetime



  # =========================================================================
    # DASHBOARD
    # =========================================================================
class DashboardMixin:
      def __init__(self):
          super().__init__()

      def mostrar_dashboard(self):
        self.tela_atual = "home"
        self.limpar_container()
        body = self._montar_layout("Dashboard", "Visao geral do dia")
        pad  = tk.Frame(body, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=16, pady=16)

        total      = len(self.pedidos)
        abertos    = sum(1 for p in self.pedidos if p["status"] in ("Em preparo","Aguardando"))
        finalizados= sum(1 for p in self.pedidos if p["status"] == "Finalizado")
        faturamento= sum(p["total"] for p in self.pedidos if p["status"] == "Finalizado")
        ocupadas   = len(mesas_ocupadas(self.pedidos))

        # Saudação + badge de banco
        saud_row = tk.Frame(pad, bg=COLORS["bg"])
        saud_row.pack(fill="x", pady=(0, 4))
        hora  = datetime.now().hour
        grt   = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
        nome_curto = (self.usuario_nome or "").split()[0] if self.usuario_nome else ""
        tk.Label(saud_row, text=f"{grt}, {nome_curto}!",
                 bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT, 16, "bold")).pack(side="left")
        db_txt = "MongoDB" if MONGO_OK else "JSON local"
        db_bg  = COLORS["green_light"] if MONGO_OK else COLORS["amber_light"]
        db_fg  = COLORS["green_dark"]  if MONGO_OK else COLORS["amber"]
        tk.Label(saud_row, text=f"  {db_txt}  ", bg=db_bg, fg=db_fg,
                 font=(FONT, 8, "bold"), padx=6, pady=2).pack(side="right")
        tk.Label(pad, text=f"Atualizado às {datetime.now().strftime('%H:%M:%S')}",
                 bg=COLORS["bg"], fg=COLORS["gray"],
                 font=(FONT, 8)).pack(anchor="w", pady=(0, 14))

        cards = tk.Frame(pad, bg=COLORS["bg"])
        cards.pack(fill="x")
        self._metric_card(cards, "Total Pedidos", str(total),          COLORS["green"],  0)
        self._metric_card(cards, "Em Aberto",     str(abertos),        COLORS["amber"],  1)
        self._metric_card(cards, "Finalizados",   str(finalizados),    COLORS["blue"],   2)
        for i in range(3): cards.columnconfigure(i, weight=1)

        # faturamento total
        fat_row = tk.Frame(pad, bg=COLORS["bg"])
        fat_row.pack(fill="x", pady=(8,0))
        fat_card = tk.Frame(fat_row, bg=COLORS["card"],
                            highlightbackground=COLORS["gray_light"], highlightthickness=1)
        fat_card.pack(fill="x")
        fat_inner = tk.Frame(fat_card, bg=COLORS["card"])
        fat_inner.pack(padx=14, pady=10, fill="x")
        tk.Label(fat_inner, text="Faturamento do dia (pedidos finalizados)",
                 bg=COLORS["card"], fg=COLORS["gray"], font=(FONT,9)).pack(side="left")
        tk.Label(fat_inner, text=brl(faturamento), bg=COLORS["card"],
                 fg=COLORS["green"], font=(FONT,13,"bold")).pack(side="right")

        # fluxo de pedidos dinâmico
        labels_f, valores_f = _calcular_fluxo(self.pedidos)
        self._secao_titulo(pad, "Fluxo de Pedidos por Hora")
        self._grafico_barras(pad, labels=labels_f, valores=valores_f, cor=COLORS["green"])

        # análise de vendas (R$) dinâmica — passa as mesmas labels do fluxo
        valores_v = _calcular_vendas(self.pedidos)
        self._secao_titulo(pad, "Faturamento por Hora  (R$)")
        self._grafico_linha(pad, valores=valores_v, cor=COLORS["green_dark"],
                            labels=labels_f)

        # ocupação das mesas — dados em tempo real
        self._secao_titulo(pad, "Ocupacao das Mesas")
        self._grafico_rosca(pad, ocupadas=ocupadas, total_mesas=TOTAL_MESAS)

        HoverButton(pad, "+ Novo Pedido", command=self.abrir_novo_pedido,
                    font_size=12).pack(fill="x", pady=(20,8))

        if self._is_admin():
            tk.Frame(pad, bg=COLORS["gray_light"], height=1).pack(fill="x", pady=(8,0))
            tk.Label(pad, text="\u26BF  Painel do Administrador",
                     bg=COLORS["bg"], fg=COLORS["dark"],
                     font=(FONT,10,"bold")).pack(anchor="w", pady=(12,6))
            HoverButton(pad, "\u2699  Gerenciar Contas de Usuarios",
                        command=self._abrir_gerenciar_usuarios,
                        bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                        font_size=11).pack(fill="x")

def _metric_card(self, parent, titulo, valor_str, cor, col):
        card = tk.Frame(parent, bg=COLORS["card"],
                        highlightbackground=COLORS["gray_light"], highlightthickness=1)
        card.grid(row=0, column=col, padx=4, sticky="nsew")
        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(padx=10, pady=14, fill="both")
        # barra colorida
        tk.Frame(inner, bg=cor, width=32, height=4).pack(anchor="w")
        # label animada
        num_var = tk.StringVar(value="0")
        lbl = tk.Label(inner, textvariable=num_var, bg=COLORS["card"],
                       fg=COLORS["dark"], font=(FONT, 26, "bold"))
        lbl.pack(anchor="w", pady=(6, 0))
        tk.Label(inner, text=titulo, bg=COLORS["card"],
                 fg=COLORS["gray"], font=(FONT, 9)).pack(anchor="w")

        # count-up animation (só para strings numéricas inteiras)
        try:
            target = int(valor_str)
            if target > 0:
                steps  = min(target, 20)
                delay  = max(1, 400 // steps)
                def _step(i=0):
                    if not num_var or not lbl.winfo_exists(): return
                    v = int(target * ((i + 1) / steps))
                    num_var.set(str(v))
                    if i < steps - 1:
                        lbl.after(delay, lambda: _step(i + 1))
                lbl.after(60, _step)
            else:
                num_var.set(valor_str)
        except ValueError:
            num_var.set(valor_str)

def _secao_titulo(self, parent, texto):
        tk.Label(parent, text=texto, bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT,12,"bold")).pack(anchor="w", pady=(22,8))

def _card_canvas(self, parent, altura):
        card = tk.Frame(parent, bg=COLORS["card"],
                        highlightbackground=COLORS["gray_light"], highlightthickness=1)
        card.pack(fill="x")
        cv = tk.Canvas(card, height=altura, bg=COLORS["card"], highlightthickness=0)
        cv.pack(fill="x", padx=14, pady=14)
        return cv

def _grafico_barras(self, parent, labels, valores, cor):
        cv = self._card_canvas(parent, 165)
        cv.update_idletasks()
        w  = cv.winfo_width() or 360
        h  = 165
        mg_l = 10; mg_r = 10; mg_t = 14; mg_b = 24
        max_v = max(valores) if any(v > 0 for v in valores) else 1
        n     = len(valores)
        plot_w = w - mg_l - mg_r
        plot_h = h - mg_t - mg_b
        by = mg_t + plot_h
        esp = plot_w / n
        bw  = esp * 0.55

        # linha de base
        cv.create_line(mg_l, by, w - mg_r, by,
                       fill=COLORS["gray_light"])

        for i, v in enumerate(valores):
            x  = mg_l + i * esp + (esp - bw) / 2
            bh = (v / max_v) * plot_h
            # barra
            cv.create_rectangle(x, by - bh, x + bw, by,
                                 fill=cor, outline="")
            # valor acima
            cv.create_text(x + bw/2, by - bh - 9,
                           text=str(v),
                           fill=COLORS["dark"], font=(FONT, 8, "bold"))
            # label hora abaixo
            cv.create_text(x + bw/2, by + 12,
                           text=labels[i],
                           fill=COLORS["gray"], font=(FONT, 8))

def _grafico_linha(self, parent, valores, cor, labels=None):
        """Gráfico de linha com área preenchida.
        labels: lista de strings para o eixo X (opcional).
        valores: lista de floats (R$).
        """
        altura = 185
        cv = self._card_canvas(parent, altura)
        cv.update_idletasks()
        w = cv.winfo_width() or 360
        h = altura
        mg_l = 52   # margem esquerda (espaço para eixo Y)
        mg_r = 16
        mg_t = 20
        mg_b = 28 if labels else 18

        max_v = max(valores) if any(v > 0 for v in valores) else 1
        n     = len(valores)
        plot_w = w - mg_l - mg_r
        plot_h = h - mg_t - mg_b
        by     = mg_t + plot_h

        passo = plot_w / max(n - 1, 1)
        pts   = [(mg_l + i * passo, by - (v / max_v) * plot_h)
                 for i, v in enumerate(valores)]

        # área preenchida
        poly = [mg_l, by] + [c for p in pts for c in p] + [mg_l + (n-1)*passo, by]
        cv.create_polygon(poly, fill=COLORS["green_light"], outline="")

        # linha
        flat = [c for p in pts for c in p]
        if len(flat) >= 4:
            cv.create_line(flat, fill=cor, width=2, smooth=True)

        # pontos + valores no topo
        for (x, y), v in zip(pts, valores):
            cv.create_oval(x-4, y-4, x+4, y+4,
                           fill=cor, outline=COLORS["white"], width=2)
            if v > 0:
                lbl = f"R${v/1000:.1f}k" if v >= 1000 else f"R${v:.0f}"
                cv.create_text(x, y - 12, text=lbl,
                               fill=COLORS["dark_soft"],
                               font=(FONT, 7, "bold"))

        # eixo Y: 3 referências
        for frac in (0, 0.5, 1.0):
            yy  = by - frac * plot_h
            val = max_v * frac
            lbl = f"R${val/1000:.0f}k" if val >= 1000 else f"R${val:.0f}"
            cv.create_line(mg_l, yy, mg_l + plot_w, yy,
                           fill=COLORS["gray_light"], dash=(3, 3))
            cv.create_text(mg_l - 4, yy, text=lbl,
                           fill=COLORS["gray"], font=(FONT, 7),
                           anchor="e")

        # eixo X: labels de hora
        if labels:
            for i, lbl in enumerate(labels):
                x = mg_l + i * passo
                cv.create_text(x, by + 12, text=lbl,
                               fill=COLORS["gray"], font=(FONT, 7))

def _grafico_rosca(self, parent, ocupadas, total_mesas):
        card = tk.Frame(parent, bg=COLORS["card"],
                        highlightbackground=COLORS["gray_light"], highlightthickness=1)
        card.pack(fill="x")
        row = tk.Frame(card, bg=COLORS["card"])
        row.pack(fill="x", padx=14, pady=14)
        cv = tk.Canvas(row, width=140, height=140,
                       bg=COLORS["card"], highlightthickness=0)
        cv.pack(side="left")

        pct = ocupadas / total_mesas if total_mesas else 0
        target_ext = -360 * pct

        # fundo cinza
        cv.create_arc(10, 10, 130, 130, start=90, extent=-360,
                      fill=COLORS["gray_light"], outline="", tags="bg_arc")
        # arco verde (animado)
        arc_id = cv.create_arc(10, 10, 130, 130, start=90, extent=0,
                               fill=COLORS["green"], outline="", tags="fg_arc")
        # furo central
        cv.create_oval(40, 40, 100, 100, fill=COLORS["card"], outline="")
        pct_lbl = cv.create_text(70, 62, text="0%",
                                 fill=COLORS["dark"], font=(FONT, 15, "bold"))
        cv.create_text(70, 80, text="ocupado",
                       fill=COLORS["gray"], font=(FONT, 8))

        # animação do arco: 24 frames
        Frame = 24
        def _step(i=1):
            if not cv.winfo_exists(): return
            t = i / Frame
            ext = target_ext * t
            pct_now = abs(ext) / 360
            cv.itemconfig(arc_id, extent=ext)
            cv.itemconfig(pct_lbl, text=f"{int(pct_now*100)}%")
            if i < Frame:
                cv.after(18, lambda: _step(i + 1))
        cv.after(80, _step)

        info = tk.Frame(row, bg=COLORS["card"])
        info.pack(side="left", padx=18)
        self._legenda(info, COLORS["green"],      f"Ocupadas: {ocupadas}")
        self._legenda(info, COLORS["gray_light"], f"Livres: {total_mesas - ocupadas}")
        tk.Label(info, text=f"Total: {total_mesas} mesas",
                 bg=COLORS["card"], fg=COLORS["dark"],
                 font=(FONT, 9, "bold")).pack(anchor="w", pady=(8, 0))

def _legenda(self, parent, cor, texto):
        row = tk.Frame(parent, bg=COLORS["card"])
        row.pack(anchor="w", pady=2)
        c = tk.Canvas(row, width=12, height=12, bg=COLORS["card"], highlightthickness=0)
        c.pack(side="left")
        c.create_oval(1,1,11,11, fill=cor, outline="")
        tk.Label(row, text=texto, bg=COLORS["card"], fg=COLORS["gray"],
                 font=(FONT,9)).pack(side="left", padx=6)
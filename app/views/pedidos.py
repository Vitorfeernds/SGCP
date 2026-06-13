import tkinter as tk
from app.theme import COLORS, FONT, HoverButton
from app.views.base import SGCPApp
from app.db.cardapio import _CARDAPIO_IDX, _indice_cardapio
import datetime

from app.logic.analytics import brl, calcular_tempo_medio
from app.db.pedidos import STATUS_CORES



   # =========================================================================
    # DETALHE DA OS
    # =========================================================================
class PedidosMixin:
    def __init__(self):
        super().__init__()

    def mostrar_pedidos(self):
        self.tela_atual = "pedidos"
        self.limpar_container()
        body = self._montar_layout("Pedidos", "Gerencie os pedidos em andamento")

        pedidos = self._listar_pedidos()

        if not pedidos:
            tk.Label(body, text="Nenhum pedido encontrado.",
                     bg=COLORS["bg"], fg=COLORS["gray"], font=(FONT, 9)).pack(pady=20)
            return

        for p in pedidos:
            fg_s, bg_s = STATUS_CORES.get(p["status"],(COLORS["gray"],COLORS["gray_light"]))
            row = tk.Frame(body, bg=COLORS["card"],
                           highlightbackground=COLORS["gray_light"], highlightthickness=1)
            row.pack(fill="x", pady=6, padx=12)
            row.bind("<Button-1>", lambda e, p=p: self._abrir_detalhe_os(p))
def _abrir_detalhe_os(self, p):
        mesa_lib = p.get("mesa_liberada", False)
        win = tk.Toplevel(self)
        win.title(f"Detalhes  {p['os']}")
        win.geometry("400x540")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        fg_s, bg_s = STATUS_CORES.get(p["status"],(COLORS["gray"],COLORS["gray_light"]))
        head = tk.Frame(win, bg=bg_s, height=72)
        head.pack(fill="x")
        head.pack_propagate(False)
        hr = tk.Frame(head, bg=bg_s)
        hr.pack(fill="x", padx=20, pady=16)
        tk.Label(hr, text=p["os"], bg=bg_s, fg=fg_s,
                 font=(FONT,18,"bold")).pack(side="left")
        if mesa_lib:
            tk.Label(hr, text="MESA LIBERADA", bg=COLORS["gray"],
                     fg=COLORS["white"], font=(FONT,8,"bold"),
                     padx=8, pady=4).pack(side="right", padx=(0,8))
        tk.Label(hr, text=p["status"], bg=fg_s, fg=COLORS["white"],
                 font=(FONT,9,"bold"), padx=10, pady=4).pack(side="right")

        body = tk.Frame(win, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=16)

        ic = tk.Frame(body, bg=COLORS["card"],
                      highlightbackground=COLORS["gray_light"], highlightthickness=1)
        ic.pack(fill="x")
        ii = tk.Frame(ic, bg=COLORS["card"])
        ii.pack(padx=14, pady=12, fill="x")

        def row(lbl, val, cor=COLORS["dark_soft"]):
            r = tk.Frame(ii, bg=COLORS["card"]); r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl, bg=COLORS["card"], fg=COLORS["gray"],
                     font=(FONT,9)).pack(side="left")
            tk.Label(r, text=val, bg=COLORS["card"], fg=cor,
                     font=(FONT,9,"bold")).pack(side="right")

        status_mesa = "Liberada" if mesa_lib else "Ocupada"
        row("Mesa",          f"Mesa {p['mesa']:02d}  [{status_mesa}]")
        row("Abertura",      p["inicio"])
        row("Total",         brl(p["total"]), COLORS["green"])

        if p["status"] in ("Aguardando","Em preparo") and not mesa_lib:
            ts = calcular_tempo_medio(p.get("itens_lista",[]))
            if ts:
                tbg = COLORS["amber_light"] if p["status"]=="Em preparo" else COLORS["blue_light"]
                tfg = COLORS["amber"]       if p["status"]=="Em preparo" else COLORS["blue"]
                tk.Frame(ii, bg=COLORS["gray_light"], height=1).pack(fill="x", pady=(8,6))
                tk.Label(tk.Frame(ii, bg=tbg),
                         text=f"\u23F3  Tempo medio de preparo: {ts}",
                         bg=tbg, fg=tfg, font=(FONT,9,"bold"),
                         padx=8, pady=5).pack(anchor="w")
                ii.winfo_children()[-1].pack(fill="x")

        tk.Label(body, text="Itens do Pedido", bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT,12,"bold")).pack(anchor="w", pady=(16,8))

        itens_lista = p.get("itens_lista",[])
        if not itens_lista:
            tk.Label(body, text="Detalhes dos itens nao disponiveis.",
                     bg=COLORS["bg"], fg=COLORS["gray"], font=(FONT,9)).pack(anchor="w")
        else:
            for entry in itens_lista:
                ri_f = tk.Frame(body, bg=COLORS["card"],
                                highlightbackground=COLORS["gray_light"], highlightthickness=1)
                ri_f.pack(fill="x", pady=3)
                ri  = tk.Frame(ri_f, bg=COLORS["card"])
                ri.pack(fill="x", padx=12, pady=8)
                tk.Label(ri, text=f"x{entry['qtd']}", bg=COLORS["dark"],
                         fg=COLORS["white"], font=(FONT,9,"bold"),
                         padx=7, pady=3).pack(side="left", padx=(0,10))
                nf = tk.Frame(ri, bg=COLORS["card"])
                nf.pack(side="left", fill="x", expand=True)
                tk.Label(nf, text=entry["nome"], bg=COLORS["card"], fg=COLORS["dark"],
                         font=(FONT,10,"bold"), anchor="w",
                         wraplength=190, justify="left").pack(anchor="w")
                d = (_CARDAPIO_IDX or _indice_cardapio()).get(entry["nome"])
                if d:
                    tk.Label(nf, text=f"\u23F1 {d.get('tempo','—')}",
                             bg=COLORS["card"], fg=COLORS["gray"],
                             font=(FONT,8)).pack(anchor="w")
                tk.Label(ri, text=brl(entry["preco"]*entry["qtd"]),
                         bg=COLORS["card"], fg=COLORS["green"],
                         font=(FONT,10,"bold")).pack(side="right")

        rod = tk.Frame(win, bg=COLORS["bg"])
        rod.pack(fill="x", padx=18, pady=12)

        if p["status"] not in ("Finalizado","Cancelado"):
            prox = {"Aguardando":"Em preparo","Em preparo":"Finalizado"}.get(p["status"],"")
            if prox:
                def _av():
                    self._avancar_status(p); win.destroy()
                HoverButton(rod, f"Avan\u00e7ar para: {prox}",
                            command=_av, font_size=11).pack(fill="x", pady=(0,8))

        if not mesa_lib:
            def _des():
                win.destroy()        # fecha o modal primeiro
                self._desocupar_mesa(p)  # então desocupa (e vai para home)
            HoverButton(rod, "Desocupar Mesa",
                        command=_des,
                        bg=COLORS["purple_light"], fg=COLORS["purple"],
                        hover_bg=COLORS["purple"],
                        font_size=10).pack(fill="x", pady=(0,8))

        HoverButton(rod, "Fechar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x")
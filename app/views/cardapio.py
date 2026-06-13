import re
import tkinter as tk
from tkinter import ttk, messagebox
 
from app.theme import COLORS, FONT, HoverButton, brl
from app.db import cardapio_db
from app.logic.cardapio import (
    reconstruir_indice, categoria_do_item, inserir_em_categoria,
)
import app.state as state
 
 
class CardapioMixin:
 
    # ── recarregar estado após qualquer edição ───────────────────────────────
 
    def _reload_cardapio(self):
        """Recarrega state.CARDAPIO do banco e reconstrói o índice."""
        state.CARDAPIO = cardapio_db.carregar(state.CARDAPIO)
        reconstruir_indice()
 
    # ── tela principal ────────────────────────────────────────────────────────
 
    def mostrar_cardapio(self):
        self.tela_atual = "cardapio"
        self.limpar_container()
        admin = self._is_admin()
        subtitulo = ("Pratos e bebidas  \u2014  Modo Admin" if admin
                      else "Pratos e bebidas  \u2014  Somente visualização")
        body = self._montar_layout("Cardápio", subtitulo)
        pad  = tk.Frame(body, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=16, pady=16)
 
        # Botões de ação — somente admin
        if admin:
            btn_row = tk.Frame(pad, bg=COLORS["bg"])
            btn_row.pack(fill="x", pady=(0, 14))
            HoverButton(btn_row, "+ Nova Receita",
                        command=self._abrir_form_receita,
                        font_size=11).pack(side="left", fill="x", expand=True,
                                           padx=(0, 6))
            HoverButton(btn_row, "+ Nova Categoria",
                        command=self._abrir_form_nova_categoria,
                        bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                        font_size=11).pack(side="left", fill="x", expand=True)
 
        # Aviso modo visualização
        if not admin:
            tk.Label(pad,
                     text="Modo visualização  \u2014  Apenas o Administrador "
                          "pode editar o cardápio.",
                     bg=COLORS["amber_light"], fg=COLORS["amber"],
                     font=(FONT, 8), padx=10, pady=6,
                     wraplength=360, justify="left").pack(fill="x", pady=(0, 12))
 
        for grupo in state.CARDAPIO:
            cat_row = tk.Frame(pad, bg=COLORS["bg"])
            cat_row.pack(fill="x", pady=(10, 4))
            tk.Label(cat_row, text=grupo["categoria"], bg=COLORS["bg"],
                     fg=COLORS["dark"], font=(FONT, 13, "bold")).pack(side="left")
            if admin:
                def _editar_cat(g=grupo):
                    self._abrir_form_categoria(g)
                HoverButton(cat_row, "Editar categoria",
                            command=_editar_cat,
                            bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                            font_size=8, padx=10, pady=4).pack(side="right")
            for item in grupo["itens"]:
                self._card_item_cardapio(pad, item, admin=admin)
 
    # ── card de item ──────────────────────────────────────────────────────────
 
    def _card_item_cardapio(self, parent, item: dict, admin: bool = False):
        card = tk.Frame(parent, bg=COLORS["card"],
                        highlightbackground=COLORS["gray_light"], highlightthickness=1)
        card.pack(fill="x", pady=5)
        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill="x", padx=12, pady=12)
 
        img = tk.Canvas(inner, width=56, height=56, bg=COLORS["card"],
                        highlightthickness=0, cursor="hand2")
        img.pack(side="left")
        img.create_rectangle(0, 0, 56, 56, fill=item["cor"], outline="")
        img.create_text(28, 28, text=item["nome"][0],
                        fill=COLORS["white"], font=(FONT, 20, "bold"))
 
        info = tk.Frame(inner, bg=COLORS["card"])
        info.pack(side="left", fill="x", expand=True, padx=10)
        tk.Label(info, text=item["nome"], bg=COLORS["card"], fg=COLORS["dark"],
                 font=(FONT, 10, "bold"), anchor="w",
                 justify="left", wraplength=160).pack(anchor="w")
        row_preco = tk.Frame(info, bg=COLORS["card"])
        row_preco.pack(anchor="w", fill="x")
        tk.Label(row_preco, text=brl(item["preco"]), bg=COLORS["card"],
                 fg=COLORS["green"], font=(FONT, 10, "bold")).pack(side="left")
        tk.Label(row_preco, text=f"  ⏱ {item.get('tempo', '—')}",
                 bg=COLORS["card"], fg=COLORS["gray"],
                 font=(FONT, 8)).pack(side="left")
        disp_bg = COLORS["green_light"] if item["disponivel"] else COLORS["red_light"]
        disp_fg = COLORS["green_dark"]  if item["disponivel"] else COLORS["red"]
        tk.Label(info, text="Disponível" if item["disponivel"] else "Indisponível",
                 bg=disp_bg, fg=disp_fg, font=(FONT, 8, "bold"),
                 padx=8, pady=2).pack(anchor="w", pady=(4, 0))
 
        acao_col = tk.Frame(inner, bg=COLORS["card"])
        acao_col.pack(side="right")
 
        if admin:
            HoverButton(acao_col, "Editar",
                        command=lambda it=item: self._abrir_form_receita(it),
                        bg=COLORS["amber_light"], fg=COLORS["amber"],
                        hover_bg=COLORS["amber"], font_size=8,
                        padx=8, pady=3).pack(pady=(0, 4))
 
        seta = tk.Label(acao_col, text="\u203a", bg=COLORS["card"],
                        fg=COLORS["gray"], font=(FONT, 18, "bold"), cursor="hand2")
        seta.pack()
        for w in (img, seta):
            w.bind("<Button-1>", lambda e, it=item: self._abrir_ficha_tecnica(it))
 
    # ── ficha técnica ────────────────────────────────────────────────────────
 
    def _abrir_ficha_tecnica(self, item: dict):
        admin = self._is_admin()
        win = tk.Toplevel(self)
        win.title("Ficha Técnica")
        win.geometry("400x660")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self); win.grab_set()
 
        head = tk.Frame(win, bg=item["cor"], height=120)
        head.pack(fill="x"); head.pack_propagate(False)
        hrow = tk.Frame(head, bg=item["cor"])
        hrow.pack(fill="x", padx=20, pady=(24, 0))
        tk.Label(hrow, text=item["nome"], bg=item["cor"], fg=COLORS["white"],
                 font=(FONT, 15, "bold"), wraplength=260,
                 justify="left").pack(side="left", anchor="w")
        if admin:
            HoverButton(hrow, "\u270e Editar",
                        command=lambda: [win.destroy(),
                                         self._abrir_form_receita(item)],
                        bg=COLORS["white"], fg=item["cor"],
                        hover_bg=COLORS["gray_light"],
                        font_size=9, padx=10, pady=4).pack(side="right", anchor="n")
        tk.Label(head, text=brl(item["preco"]), bg=item["cor"],
                 fg=COLORS["white"], font=(FONT, 12)).pack(anchor="w", padx=20)
 
        wrap = tk.Frame(win, bg=COLORS["bg"])
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
        cv.bind("<Enter>", lambda e: cv.bind_all(
            "<MouseWheel>", lambda ev: cv.yview_scroll(int(-1*(ev.delta/120)), "units")))
        cv.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
 
        body = tk.Frame(sf, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=16)
 
        meta_card = tk.Frame(body, bg=COLORS["card"],
                             highlightbackground=COLORS["gray_light"], highlightthickness=1)
        meta_card.pack(fill="x", pady=(0, 12))
        meta = tk.Frame(meta_card, bg=COLORS["card"])
        meta.pack(fill="x", padx=14, pady=10)
 
        def _mrow(lbl, val, vc=None):
            vc = vc or COLORS["dark_soft"]
            r = tk.Frame(meta, bg=COLORS["card"]); r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl, bg=COLORS["card"], fg=COLORS["gray"],
                     font=(FONT, 9)).pack(side="left")
            tk.Label(r, text=val, bg=COLORS["card"], fg=vc,
                     font=(FONT, 9, "bold")).pack(side="right")
 
        _mrow("Tempo de preparo", item.get("tempo", "—"))
        _mrow("Disponibilidade",
              "Disponível" if item["disponivel"] else "Indisponível",
              COLORS["green"] if item["disponivel"] else COLORS["red"])
        _mrow("Categoria", categoria_do_item(item["nome"]))
 
        tk.Label(body, text="Ingredientes", bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(8, 6))
        for ing in item.get("ingredientes", []):
            tk.Label(body, text=f"\u2022  {ing}", bg=COLORS["bg"],
                     fg=COLORS["dark_soft"], font=(FONT, 10),
                     anchor="w", wraplength=340, justify="left").pack(anchor="w", pady=1)
 
        tk.Label(body, text="Modo de Preparo", bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(14, 6))
        for i, passo in enumerate(item.get("modo", []), 1):
            linha = tk.Frame(body, bg=COLORS["bg"])
            linha.pack(fill="x", anchor="w", pady=3)
            tk.Label(linha, text=str(i), bg=COLORS["green"], fg=COLORS["white"],
                     font=(FONT, 9, "bold"), width=2).pack(side="left", padx=(0, 8))
            tk.Label(linha, text=passo, bg=COLORS["bg"], fg=COLORS["dark_soft"],
                     font=(FONT, 10), wraplength=310, justify="left").pack(
                         side="left", anchor="w")
 
        HoverButton(win, "Fechar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"]).pack(
                        fill="x", padx=20, pady=12)
 
    # ── formulário receita (criar / editar) ──────────────────────────────────
 
    def _abrir_form_receita(self, item: dict | None = None):
        """item=None → criar nova receita; item=dict → editar existente."""
        if not self._is_admin():
            messagebox.showerror("Acesso negado",
                                 "Apenas o Administrador pode editar receitas.")
            return
 
        modo_edicao = item is not None
        titulo_win  = "Editar Receita" if modo_edicao else "Nova Receita"
 
        win = tk.Toplevel(self)
        win.title(titulo_win)
        win.geometry("420x760")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, True)
        win.transient(self); win.grab_set()
 
        head = tk.Frame(win, bg=COLORS["dark"], height=64)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text=titulo_win, bg=COLORS["dark"], fg=COLORS["white"],
                 font=(FONT, 14, "bold")).pack(side="left", padx=20, pady=18)
        tk.Label(head, text="ADMIN", bg=COLORS["green"], fg=COLORS["white"],
                 font=(FONT, 8, "bold"), padx=8, pady=3).pack(side="right", padx=18)
 
        wrap = tk.Frame(win, bg=COLORS["bg"])
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
        cv.bind("<Enter>", lambda e: cv.bind_all(
            "<MouseWheel>", lambda ev: cv.yview_scroll(int(-1*(ev.delta/120)), "units")))
        cv.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
 
        pad = tk.Frame(sf, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=18, pady=16)
 
        # ── helper: campo de texto simples ──────────────────────────────────
        def _campo(lbl, val="", show=None):
            tk.Label(pad, text=lbl, bg=COLORS["bg"], fg=COLORS["dark_soft"],
                     font=(FONT, 9, "bold")).pack(anchor="w", pady=(8, 0))
            e = tk.Entry(pad, font=(FONT, 11), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"], highlightthickness=1)
            if show: e.config(show=show)
            e.pack(fill="x", ipady=7, pady=(4, 0))
            if val: e.insert(0, str(val))
            return e
 
        # ── helper: lista editável (ingredientes / passos) ──────────────────
        def _lista_editavel(lbl, valores_iniciais: list):
            tk.Label(pad, text=lbl, bg=COLORS["bg"], fg=COLORS["dark_soft"],
                     font=(FONT, 9, "bold")).pack(anchor="w", pady=(14, 4))
            container = tk.Frame(pad, bg=COLORS["bg"])
            container.pack(fill="x")
            entradas: list = []
 
            def _add_linha(texto=""):
                row = tk.Frame(container, bg=COLORS["bg"])
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{len(entradas)+1}.", bg=COLORS["bg"],
                         fg=COLORS["gray"], font=(FONT, 9), width=2).pack(
                             side="left", padx=(0, 6))
                e = tk.Entry(row, font=(FONT, 10), relief="flat",
                             bg=COLORS["card"], fg=COLORS["dark"],
                             insertbackground=COLORS["dark"],
                             highlightbackground=COLORS["gray_light"], highlightthickness=1)
                e.pack(side="left", fill="x", expand=True, ipady=5)
                if texto: e.insert(0, texto)
 
                def _remover(r=row, en=e):
                    entradas.remove(en)
                    r.destroy()
                    for idx, ef in enumerate(entradas, 1):
                        ef.master.winfo_children()[0].config(text=f"{idx}.")
 
                btn_rm = tk.Label(row, text="\u2715", bg=COLORS["bg"],
                                  fg=COLORS["red"], font=(FONT, 10, "bold"),
                                  cursor="hand2", padx=6)
                btn_rm.pack(side="right")
                btn_rm.bind("<Button-1>", lambda e: _remover())
                entradas.append(e)
 
            for v in valores_iniciais:
                _add_linha(v)
 
            HoverButton(container, "+ Adicionar linha",
                        command=_add_linha,
                        bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                        font_size=9, padx=10, pady=4).pack(anchor="w", pady=(6, 0))
 
            return lambda: [e.get().strip() for e in entradas if e.get().strip()]
 
        # ── campos principais ────────────────────────────────────────────────
        f_nome  = _campo("Nome do prato / bebida",
                         item["nome"] if modo_edicao else "")
        f_preco = _campo("Preço (R$)",
                         f"{item['preco']:.2f}".replace(".", ",") if modo_edicao else "")
        f_tempo = _campo("Tempo de preparo (ex: 25 min)",
                         item.get("tempo", "") if modo_edicao else "")
 
        # disponibilidade
        tk.Label(pad, text="Disponibilidade", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w", pady=(10, 4))
        disp_var = tk.BooleanVar(value=item.get("disponivel", True) if modo_edicao else True)
        disp_row = tk.Frame(pad, bg=COLORS["bg"])
        disp_row.pack(anchor="w")
        for txt, val in [("Disponível", True), ("Indisponível", False)]:
            tk.Radiobutton(disp_row, text=txt, variable=disp_var, value=val,
                           bg=COLORS["bg"], fg=COLORS["dark_soft"],
                           selectcolor=COLORS["green_light"], font=(FONT, 10),
                           activebackground=COLORS["bg"]).pack(side="left", padx=(0, 14))
 
        # cor com preview ao vivo
        tk.Label(pad, text="Cor do avatar (hex, ex: #7C2D12)", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w", pady=(10, 0))
        cor_row = tk.Frame(pad, bg=COLORS["bg"])
        cor_row.pack(fill="x", pady=(4, 0))
        f_cor = tk.Entry(cor_row, font=(FONT, 11), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"], highlightthickness=1)
        f_cor.pack(side="left", fill="x", expand=True, ipady=7)
        preview_cv = tk.Canvas(cor_row, width=40, height=36,
                               bg=COLORS["card"], highlightthickness=0)
        preview_cv.pack(side="left", padx=(6, 0))
        cor_inicial = item.get("cor", "#374151") if modo_edicao else "#374151"
        preview_cv.create_rectangle(0, 0, 40, 36, fill=cor_inicial, outline="")
        preview_cv.create_text(20, 18,
                               text=item["nome"][0].upper() if modo_edicao else "A",
                               fill=COLORS["white"], font=(FONT, 14, "bold"), tags="letra")
        if modo_edicao: f_cor.insert(0, cor_inicial)
 
        def _atualizar_preview(*_):
            cor = f_cor.get().strip()
            if re.match(r"^#[0-9A-Fa-f]{6}$", cor):
                preview_cv.itemconfig("all", fill=cor)
                preview_cv.itemconfig("letra", fill=COLORS["white"])
        f_cor.bind("<KeyRelease>", _atualizar_preview)
        f_cor.bind("<FocusOut>",   _atualizar_preview)
 
        # categoria
        cats = [g["categoria"] for g in state.CARDAPIO]
        if modo_edicao:
            cat_atual = categoria_do_item(item["nome"])
        else:
            cat_atual = cats[0] if cats else ""
 
        tk.Label(pad, text="Categoria", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w", pady=(10, 0))
        cat_var = tk.StringVar(value=cat_atual)
        ttk.Combobox(pad, textvariable=cat_var, values=cats,
                     font=(FONT, 10)).pack(fill="x", pady=(4, 0), ipady=4)
 
        get_ings = _lista_editavel("Ingredientes",
                                   item.get("ingredientes", []) if modo_edicao else [])
        get_modo = _lista_editavel("Modo de Preparo",
                                   item.get("modo", []) if modo_edicao else [])
 
        tk.Frame(pad, bg=COLORS["gray_light"], height=1).pack(fill="x", pady=(18, 0))
 
        # ── excluir (somente edição) ─────────────────────────────────────────
        if modo_edicao:
            def _excluir():
                if not messagebox.askyesno(
                        "Excluir receita",
                        f"Excluir permanentemente '{item['nome']}'?", parent=win):
                    return
                for grupo in state.CARDAPIO:
                    grupo["itens"] = [it for it in grupo["itens"]
                                      if it["nome"] != item["nome"]]
                state.CARDAPIO = [g for g in state.CARDAPIO if g["itens"]]
                cardapio_db.salvar(state.CARDAPIO)
                self._reload_cardapio()
                messagebox.showinfo("Excluído",
                                    f"'{item['nome']}' removido do cardápio.")
                win.destroy()
                self.mostrar_cardapio()
 
            HoverButton(pad, "\u26b2  Excluir esta receita",
                        command=_excluir,
                        bg=COLORS["red_light"], fg=COLORS["red"],
                        hover_bg=COLORS["red"], font_size=10).pack(fill="x", pady=(12, 0))
 
        # ── salvar ────────────────────────────────────────────────────────────
        def _salvar():
            nome    = f_nome.get().strip()
            preco_s = f_preco.get().strip().replace(",", ".")
            tempo   = f_tempo.get().strip()
            cor     = f_cor.get().strip() or "#374151"
            cat     = cat_var.get().strip()
            ings    = get_ings()
            modo_p  = get_modo()
 
            if not nome:
                messagebox.showerror("Erro", "Informe o nome do prato.", parent=win); return
            try:
                preco = round(float(preco_s), 2)
                if preco <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro", "Preço inválido. Use ex: 29,90", parent=win)
                return
            if not cat:
                messagebox.showerror("Erro", "Selecione ou digite a categoria.", parent=win)
                return
 
            if not modo_edicao:
                todos_nomes = [it["nome"].lower()
                               for g in state.CARDAPIO for it in g["itens"]]
                if nome.lower() in todos_nomes:
                    messagebox.showerror(
                        "Erro", f"Já existe uma receita com o nome '{nome}'.", parent=win)
                    return
 
            if not re.match(r"^#[0-9A-Fa-f]{6}$", cor):
                cor = "#374151"
 
            tempo_norm = tempo.strip()
            if tempo_norm:
                m = re.match(r"^(\d+)\s*(min)?$", tempo_norm, re.I)
                tempo_norm = f"{m.group(1)} min" if m else tempo_norm
            else:
                tempo_norm = "—"
 
            novo_item = {
                "nome": nome, "preco": preco, "tempo": tempo_norm,
                "disponivel": disp_var.get(), "cor": cor,
                "ingredientes": ings, "modo": modo_p,
            }
 
            if modo_edicao:
                nome_antigo = item["nome"]
                for grupo in state.CARDAPIO:
                    for idx, it in enumerate(grupo["itens"]):
                        if it["nome"] == nome_antigo:
                            grupo["itens"][idx] = novo_item
                            if grupo["categoria"] != cat:
                                grupo["itens"].pop(idx)
                                inserir_em_categoria(cat, novo_item)
                            break
                    else:
                        continue
                    break
            else:
                inserir_em_categoria(cat, novo_item)
 
            cardapio_db.salvar(state.CARDAPIO)
            self._reload_cardapio()
            messagebox.showinfo(
                "Salvo",
                f"'{nome}' {'atualizado' if modo_edicao else 'adicionado'} com sucesso!")
            win.destroy()
            self.mostrar_cardapio()
 
        HoverButton(pad, "\u2714  Salvar Receita", command=_salvar,
                    font_size=12).pack(fill="x", pady=(10, 0))
        HoverButton(win, "Cancelar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=18, pady=10)
 
    # ── formulário nova categoria ─────────────────────────────────────────────
 
    def _abrir_form_nova_categoria(self):
        if not self._is_admin():
            return
        win = tk.Toplevel(self)
        win.title("Nova Categoria")
        win.geometry("380x240")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self); win.grab_set()
 
        head = tk.Frame(win, bg=COLORS["dark"], height=56)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text="Nova Categoria", bg=COLORS["dark"], fg=COLORS["white"],
                 font=(FONT, 13, "bold")).pack(side="left", padx=20, pady=14)
        tk.Label(head, text="ADMIN", bg=COLORS["green"], fg=COLORS["white"],
                 font=(FONT, 8, "bold"), padx=8, pady=3).pack(side="right", padx=18)
 
        pad = tk.Frame(win, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)
 
        tk.Label(pad, text="Nome da nova categoria", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w")
        e_cat = tk.Entry(pad, font=(FONT, 12), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"], highlightthickness=1)
        e_cat.pack(fill="x", ipady=8, pady=(4, 14))
        e_cat.focus_set()
 
        def _criar():
            nome_cat = e_cat.get().strip()
            if not nome_cat:
                messagebox.showerror("Erro", "Informe o nome da categoria.", parent=win)
                return
            if any(g["categoria"].lower() == nome_cat.lower() for g in state.CARDAPIO):
                messagebox.showerror("Erro", "Já existe uma categoria com este nome.",
                                     parent=win)
                return
            state.CARDAPIO.append({"categoria": nome_cat, "itens": []})
            cardapio_db.salvar(state.CARDAPIO)
            self._reload_cardapio()
            messagebox.showinfo(
                "Criada",
                f"Categoria '{nome_cat}' criada com sucesso!\n"
                f"Adicione receitas a ela pelo botão '+ Nova Receita'.")
            win.destroy()
            self.mostrar_cardapio()
 
        e_cat.bind("<Return>", lambda e: _criar())
        HoverButton(pad, "\u2714  Criar Categoria", command=_criar,
                    font_size=11).pack(fill="x", pady=(0, 8))
        HoverButton(win, "Cancelar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=20, pady=(0, 12))
 
    # ── formulário editar categoria ───────────────────────────────────────────
 
    def _abrir_form_categoria(self, grupo: dict):
        if not self._is_admin():
            return
        win = tk.Toplevel(self)
        win.title("Editar Categoria")
        win.geometry("380x280")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self); win.grab_set()
 
        head = tk.Frame(win, bg=COLORS["dark"], height=56)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text="Editar Categoria", bg=COLORS["dark"], fg=COLORS["white"],
                 font=(FONT, 13, "bold")).pack(side="left", padx=20, pady=14)
 
        pad = tk.Frame(win, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)
 
        tk.Label(pad, text="Nome da categoria", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w")
        e_cat = tk.Entry(pad, font=(FONT, 12), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"], highlightthickness=1)
        e_cat.pack(fill="x", ipady=8, pady=(4, 12))
        e_cat.insert(0, grupo["categoria"])
 
        def _salvar_cat():
            novo_nome = e_cat.get().strip()
            if not novo_nome:
                messagebox.showerror("Erro", "Nome não pode ser vazio.", parent=win)
                return
            grupo["categoria"] = novo_nome
            cardapio_db.salvar(state.CARDAPIO)
            self._reload_cardapio()
            win.destroy()
            self.mostrar_cardapio()
 
        def _excluir_cat():
            if grupo["itens"]:
                messagebox.showerror(
                    "Não permitido",
                    "Remova todos os itens da categoria antes de excluí-la.", parent=win)
                return
            if not messagebox.askyesno(
                    "Confirmar", f"Excluir a categoria '{grupo['categoria']}'?", parent=win):
                return
            state.CARDAPIO = [g for g in state.CARDAPIO if g is not grupo]
            cardapio_db.salvar(state.CARDAPIO)
            self._reload_cardapio()
            win.destroy()
            self.mostrar_cardapio()
 
        HoverButton(pad, "\u2714  Salvar nome", command=_salvar_cat,
                    font_size=11).pack(fill="x", pady=(0, 8))
        HoverButton(pad, "\u26b2  Excluir categoria (se vazia)",
                    command=_excluir_cat,
                    bg=COLORS["red_light"], fg=COLORS["red"],
                    hover_bg=COLORS["red"], font_size=10).pack(fill="x")
        HoverButton(win, "Cancelar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=20, pady=10)
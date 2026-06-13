import tkinter as tk
from tkinter import ttk, messagebox
 
from app.theme import COLORS, FONT, HoverButton
from app.config import PERFIL_ADMIN, PERFIL_ATENDENTE
from app.logic.auth import cadastrar, remover
from app.db.usuarios import carregar
 
 
class UsuariosMixin:
 
    def _abrir_gerenciar_usuarios(self):
        if not self._is_admin():
            messagebox.showerror("Acesso negado",
                                 "Apenas o Administrador pode gerenciar contas.")
            return
 
        win = tk.Toplevel(self)
        win.title("Gerenciar Usuários")
        win.geometry("420x680")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self); win.grab_set()
 
        head = tk.Frame(win, bg=COLORS["dark"], height=64)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text="Gerenciar Usuários", bg=COLORS["dark"],
                 fg=COLORS["white"], font=(FONT, 14, "bold")).pack(
                     side="left", padx=20, pady=18)
        tk.Label(head, text="  ADMIN  ", bg=COLORS["green"],
                 fg=COLORS["white"], font=(FONT, 8, "bold"),
                 padx=6, pady=2).pack(side="right", padx=18)
 
        bw = tk.Frame(win, bg=COLORS["bg"])
        bw.pack(fill="both", expand=True)
        cg = tk.Canvas(bw, bg=COLORS["bg"], highlightthickness=0)
        sg = ttk.Scrollbar(bw, orient="vertical", command=cg.yview)
        sf = tk.Frame(cg, bg=COLORS["bg"])
        sf.bind("<Configure>", lambda e: cg.configure(scrollregion=cg.bbox("all")))
        wi = cg.create_window((0, 0), window=sf, anchor="nw")
        cg.bind("<Configure>", lambda e: cg.itemconfig(wi, width=e.width))
        cg.configure(yscrollcommand=sg.set)
        cg.pack(side="left", fill="both", expand=True)
        sg.pack(side="right", fill="y")
 
        pad = tk.Frame(sf, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=16, pady=16)
 
        lista_f = tk.Frame(pad, bg=COLORS["bg"])
        lista_f.pack(fill="x")
 
        # ── lista de usuários ────────────────────────────────────────────────
        def _render():
            for w in lista_f.winfo_children():
                w.destroy()
            tk.Label(lista_f, text="Usuários cadastrados",
                     bg=COLORS["bg"], fg=COLORS["dark"],
                     font=(FONT, 12, "bold")).pack(anchor="w", pady=(0, 8))
            for email_u, dados in carregar().items():
                cu = tk.Frame(lista_f, bg=COLORS["card"],
                              highlightbackground=COLORS["gray_light"],
                              highlightthickness=1)
                cu.pack(fill="x", pady=4)
                ru = tk.Frame(cu, bg=COLORS["card"])
                ru.pack(fill="x", padx=12, pady=10)
 
                perfil = dados.get("perfil", PERFIL_ATENDENTE)
                pbg = COLORS["green"] if perfil == PERFIL_ADMIN else COLORS["blue"]
                tk.Label(ru, text=perfil.upper(), bg=pbg, fg=COLORS["white"],
                         font=(FONT, 8, "bold"), padx=6, pady=2).pack(
                             side="left", padx=(0, 10))
 
                iu = tk.Frame(ru, bg=COLORS["card"])
                iu.pack(side="left", fill="x", expand=True)
                tk.Label(iu, text=dados.get("nome", "—"), bg=COLORS["card"],
                         fg=COLORS["dark"], font=(FONT, 10, "bold")).pack(anchor="w")
                tk.Label(iu, text=email_u, bg=COLORS["card"],
                         fg=COLORS["gray"], font=(FONT, 8)).pack(anchor="w")
 
                if email_u != self.usuario_logado:
                    def _rem(e=email_u):
                        if messagebox.askyesno("Confirmar", f"Remover {e}?",
                                               parent=win):
                            ok, msg = remover(e, self.usuario_logado)
                            (messagebox.showinfo if ok
                             else messagebox.showerror)("Resultado", msg, parent=win)
                            if ok:
                                _render()
                    HoverButton(ru, "Remover", command=_rem,
                                bg=COLORS["red_light"], fg=COLORS["red"],
                                hover_bg=COLORS["red"], font_size=8,
                                padx=8, pady=3).pack(side="right")
 
        _render()
 
        # ── formulário de criação ────────────────────────────────────────────
        tk.Frame(pad, bg=COLORS["gray_light"], height=1).pack(fill="x", pady=(20, 16))
        tk.Label(pad, text="Criar nova conta de funcionário",
                 bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(0, 10))
 
        fc = tk.Frame(pad, bg=COLORS["card"],
                      highlightbackground=COLORS["gray_light"], highlightthickness=1)
        fc.pack(fill="x")
        fm = tk.Frame(fc, bg=COLORS["card"])
        fm.pack(padx=16, pady=16, fill="x")
 
        def _campo(lbl, **kw):
            tk.Label(fm, text=lbl, bg=COLORS["card"], fg=COLORS["dark_soft"],
                     font=(FONT, 9, "bold")).pack(anchor="w")
            e = tk.Entry(fm, font=(FONT, 11), relief="flat",
                         bg=COLORS["bg"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"], **kw)
            e.pack(fill="x", ipady=7, pady=(4, 12))
            return e
 
        fn  = _campo("Nome completo")
        fe  = _campo("E-mail")
        fs  = _campo("Senha (mínimo 6 caracteres)", show="*")
        fc2 = _campo("Confirmar senha", show="*")
 
        tk.Label(fm, text="Perfil de acesso", bg=COLORS["card"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w")
        pv = tk.StringVar(value=PERFIL_ATENDENTE)
        pf = tk.Frame(fm, bg=COLORS["card"]); pf.pack(fill="x", pady=(4, 12))
        for val, lbl_p in [(PERFIL_ATENDENTE, "Atendente"),
                          (PERFIL_ADMIN, "Administrador")]:
            tk.Radiobutton(pf, text=lbl_p, variable=pv, value=val,
                           bg=COLORS["card"], fg=COLORS["dark_soft"],
                           selectcolor=COLORS["green_light"],
                           font=(FONT, 10),
                           activebackground=COLORS["card"]).pack(
                               side="left", padx=(0, 16))
 
        def _criar():
            s, c = fs.get().strip(), fc2.get().strip()
            if s != c:
                messagebox.showerror("Erro", "As senhas não conferem.", parent=win)
                return
            ok, msg = cadastrar(fe.get().strip(), s, fn.get().strip(), pv.get())
            (messagebox.showinfo if ok else messagebox.showerror)(
                "Resultado", msg, parent=win)
            if ok:
                for e in (fn, fe, fs, fc2):
                    e.delete(0, tk.END)
                pv.set(PERFIL_ATENDENTE)
                _render()
 
        HoverButton(fm, "Criar conta", command=_criar, font_size=11).pack(fill="x")
        fc2.bind("<Return>", lambda e: _criar())
 
        HoverButton(win, "Fechar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=16, pady=12)
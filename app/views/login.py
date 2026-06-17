import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
from app.theme import COLORS, FONT, HoverButton 
from app.logic.auth import autenticar
from app.config import PERFIL_ADMIN
from app.db.connection import MONGO_OK

class LoginMixin:
    def __init__(self):
        super().__init__()
        self.mostrar_login()

    def mostrar_login(self):
        self.tela_atual = "login"
        
        wrap = tk.Frame(self.container, bg=COLORS["dark"])
        wrap.pack(fill="both", expand=True)

        # Centraliza verticalmente usando frames expansíveis
        tk.Frame(wrap, bg=COLORS["dark"]).pack(fill="both", expand=True)
        center = tk.Frame(wrap, bg=COLORS["dark"])
        center.pack(anchor="center")
        tk.Frame(wrap, bg=COLORS["dark"]).pack(fill="both", expand=True)

        # Marca
        marca = tk.Frame(center, bg=COLORS["dark"])
        marca.pack(pady=(0, 10))
        logo = tk.Canvas(marca, width=88, height=88, bg=COLORS["dark"],
                         highlightthickness=0)
        logo.pack()
        logo.create_oval(8, 8, 80, 80, fill=COLORS["green"], outline="")
        logo.create_text(44, 44, text="G", fill=COLORS["white"],
                         font=(FONT, 38, "bold"))
        tk.Label(center, text="S.G.C.P", bg=COLORS["dark"],
                 fg=COLORS["white"], font=(FONT, 26, "bold")).pack(pady=(14, 0))
        tk.Label(center, text="Guanambusiness  \u2014  Gestao de Pedidos",
                 bg=COLORS["dark"], fg=COLORS["green"],
                 font=(FONT, 11)).pack(pady=(2, 0))

        # Card de login
        card = tk.Frame(center, bg=COLORS["card"])
        card.pack(padx=28, pady=28, fill="x", ipadx=2)
        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(padx=24, pady=24, fill="x")

        tk.Label(inner, text="Acesse sua conta", bg=COLORS["card"],
                 fg=COLORS["dark"], font=(FONT, 15, "bold")).pack(anchor="w")
        tk.Label(inner, text="Entre com suas credenciais para continuar",
                 bg=COLORS["card"], fg=COLORS["gray"],
                 font=(FONT, 9)).pack(anchor="w", pady=(0, 16))

        def campo(lbl, **kw):
            tk.Label(inner, text=lbl, bg=COLORS["card"], fg=COLORS["dark_soft"],
                     font=(FONT, 9, "bold")).pack(anchor="w")
            e = tk.Entry(inner, font=(FONT, 11), relief="flat",
                         bg=COLORS["bg"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"], **kw)
            e.pack(fill="x", ipady=8, pady=(4, 14))
            return e

        self.entry_email = campo("E-mail")
        self.entry_email.insert(0, "atendente@guanambusiness.com")
        self.entry_senha = campo("Senha", show="*")
        self.entry_senha.insert(0, "123456")

        # Label de status (erros inline — sem messagebox)
        self._login_status = tk.Label(inner, text="", bg=COLORS["card"],
                                      fg=COLORS["red"], font=(FONT, 9),
                                      wraplength=280, justify="center")
        self._login_status.pack(pady=(0, 8))

        self._btn_login = HoverButton(inner, "Entrar",
                                      command=self._validar_login)
        self._btn_login.pack(fill="x")
        self.entry_senha.bind("<Return>", lambda e: self._validar_login())

        tk.Label(inner, text="Credenciais fornecidas pelo administrador",
                 bg=COLORS["card"], fg=COLORS["gray"],
                 font=(FONT, 8), wraplength=260,
                 justify="center").pack(pady=(10, 0))

        # Rodapé
        modo_txt = "MongoDB" if MONGO_OK else "JSON local"
        modo_cor = COLORS["green"] if MONGO_OK else COLORS["amber"]
        tk.Label(wrap, text=f"v1.0  \u2014  {modo_txt}", bg=COLORS["dark"],
                 fg=modo_cor, font=(FONT, 8)).pack(side="bottom", pady=12)

    def _validar_login(self):
        email = self.entry_email.get().strip()
        senha = self.entry_senha.get().strip()

        def _show_err(msg):
            try:
                self._login_status.config(text=msg, fg=COLORS["red"])
            except Exception:
                pass

        if not email or "@" not in email:
            _show_err("Informe um e-mail valido.")
            return
        if len(senha) < 6:
            _show_err("Senha com ao menos 6 caracteres.")
            return

        try:
            self._btn_login.config(text="Verificando...", cursor="watch")
        except Exception:
            pass
        self.update_idletasks()

        u = autenticar(email, senha)
        try:
            self._btn_login.config(text="Entrar", cursor="hand2")
        except Exception:
            pass

        if u is None:
            _show_err("E-mail ou senha incorretos.")
            return
        self.usuario_logado = email
        self.usuario_nome = u.get("nome", email)
        self._admin_cache = (u.get("perfil") == PERFIL_ADMIN)
        self._ultimo_hash = None  # força refresh no próximo tick
        self.navegar("home")

    def _logout(self):
        if messagebox.askyesno("Sair", "Deseja encerrar a sessao?"):
            self.usuario_logado = None
            self.usuario_nome = None
            self._admin_cache = None
            self.mostrar_login()

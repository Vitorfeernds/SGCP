import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import math
import random
import json
import os
import hashlib
import copy
import re
import threading
import time
import platform
from collections import defaultdict
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# ============================================================================
# CAMINHOS E CONSTANTES
# ============================================================================
if getattr(sys, "frozen", False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(_BASE_DIR, "data")
USUARIOS_FILE  = os.path.join(DATA_DIR, "usuarios.json")
PEDIDOS_FILE   = os.path.join(DATA_DIR, "pedidos.json")
CARDAPIO_FILE  = os.path.join(DATA_DIR, "cardapio.json")
ENV_FILE       = os.path.join(DATA_DIR, ".env")
GITIGNORE_FILE = os.path.join(_BASE_DIR, ".gitignore")

PERFIL_ADMIN     = "admin"
PERFIL_ATENDENTE = "atendente"

TOTAL_MESAS = 14   # mesas existentes no estabelecimento

# ============================================================================
# MONGODB — camada de abstração com fallback para JSON local
# ============================================================================
_mongo_client = None
_mongo_db     = None
_MONGO_OK     = False   # True somente quando conexão real estiver ativa

# ============================================================================
# Conexão com MongoDB Atlas
# ============================================================================

def _ler_env() -> dict:
    #Lê o data/.env e retorna dict de chave=valor.
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def _inicializar_mongo():
    #Tenta conectar ao MongoDB usando MONGO_URI do .env.
    #Se falhar, _MONGO_OK permanece False e o sistema usa JSON local.
    #Se conectar com sucesso, semeia dados iniciais se as coleções estiverem vazias.
    global _mongo_client, _mongo_db, _MONGO_OK
    env = _ler_env()
    uri = env.get("MONGO_URI", "")
    if not uri:
        return
    try:
        import pymongo
        _mongo_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        _mongo_client.server_info()          # força a conexão
        db_name = env.get("MONGO_DB", "sgcp")
        _mongo_db = _mongo_client[db_name]
        _MONGO_OK = True
        print(f"[DB] MongoDB conectado: {db_name}")
        _seed_mongo()
    except Exception as e:
        _MONGO_OK = False
        print(f"[DB] MongoDB indisponivel ({e}). Usando JSON local.")


def _seed_mongo():
    #Semeia dados iniciais no MongoDB se as coleções estiverem vazias.
    #Também importa dados do JSON local para o MongoDB na primeira vez.
    if not _MONGO_OK:
        return

    # Importar usuários do JSON local → MongoDB (migração automática)
    if _mongo_db["usuarios"].count_documents({}) == 0:
        if os.path.exists(USUARIOS_FILE):
            dados = _json_load(USUARIOS_FILE, {})
            if dados:
                for email, u in dados.items():
                    _mongo_db["usuarios"].update_one(
                        {"email": email},
                        {"$set": {**u, "email": email}},
                        upsert=True)
                print(f"[DB] {len(dados)} usuario(s) migrado(s) para MongoDB.")
        else:
            # Cria usuários padrão direto no MongoDB
            for email, dados_u in [
                ("admin@guanambusiness.com",
                 {"hash_senha": _hash_senha("admin123"),
                  "nome": "Administrador", "perfil": "admin"}),
                ("atendente@guanambusiness.com",
                 {"hash_senha": _hash_senha("123456"),
                  "nome": "Atendente Padrao", "perfil": "atendente"}),
            ]:
                _mongo_db["usuarios"].update_one(
                    {"email": email},
                    {"$set": {**dados_u, "email": email}},
                    upsert=True)
            print("[DB] Usuarios padrao criados no MongoDB.")

    # Importar pedidos do JSON local → MongoDB (migração automática)
    if _mongo_db["pedidos"].count_documents({}) == 0:
        if os.path.exists(PEDIDOS_FILE):
            pedidos = _json_load(PEDIDOS_FILE, [])
            if pedidos:
                _mongo_db["pedidos"].insert_many(
                    [{k: v for k, v in p.items()} for p in pedidos])
                print(f"[DB] {len(pedidos)} pedido(s) migrado(s) para MongoDB.")

    # Importar cardápio do JSON local → MongoDB (migração automática)
    if _mongo_db["cardapio"].count_documents({}) == 0:
        if os.path.exists(CARDAPIO_FILE):
            grupos = _json_load(CARDAPIO_FILE, [])
            if grupos:
                _mongo_db["cardapio"].insert_many(
                    [{k: v for k, v in g.items()} for g in grupos])
                print(f"[DB] {len(grupos)} grupo(s) do cardapio migrado(s) para MongoDB.")


# ── helpers de persistência ──────────────────────────────────────────────────

def _json_load(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
               conteudo = f.read().strip()
               if not conteudo:
                   return default
               return json.loads(conteudo)
        except json.JSONDecodeError as e:
          print(f"[DB] JSON invalido em {path}: {e}. Usando valor padrao.")
          return default
    return default


def _json_save(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── PEDIDOS ───────────────────────────────────────────────────────────────────

def db_pedidos_carregar() -> list:
    if _MONGO_OK:
        docs = list(_mongo_db["pedidos"].find({}, {"_id": 0}))
        docs.sort(key=lambda d: d.get("os", ""), reverse=True)
        return docs
    return _json_load(PEDIDOS_FILE, [])


def db_pedido_salvar(pedido: dict) -> None:
    #Insere ou atualiza um pedido (upsert por 'os').
    if _MONGO_OK:
        _mongo_db["pedidos"].update_one(
            {"os": pedido["os"]}, {"$set": pedido}, upsert=True)
    else:
        pedidos = _json_load(PEDIDOS_FILE, [])
        idx = next((i for i, p in enumerate(pedidos) if p["os"] == pedido["os"]), -1)
        if idx >= 0:
            pedidos[idx] = pedido
        else:
            pedidos.insert(0, pedido)
        _json_save(PEDIDOS_FILE, pedidos)


def db_pedido_atualizar_campo(os_num: str, campo: str, valor) -> None:
    #Atualiza um único campo de um pedido já existente.
    if _MONGO_OK:
        _mongo_db["pedidos"].update_one({"os": os_num}, {"$set": {campo: valor}})
    else:
        pedidos = _json_load(PEDIDOS_FILE, [])
        for p in pedidos:
            if p["os"] == os_num:
                p[campo] = valor
                break
        _json_save(PEDIDOS_FILE, pedidos)


# ── CARDÁPIO ──────────────────────────────────────────────────────────────────

def db_cardapio_carregar() -> list:
    # Carrega o cardápio do banco. Se ainda não existir, usa o cardápio padrão compilado no código e o persiste para edições futuras.
    if _MONGO_OK:
        grupos = list(_mongo_db["cardapio"].find({}, {"_id": 0}))
        return _normalizar_cardapio(grupos if grupos else _seed_cardapio_db())
    dados = _json_load(CARDAPIO_FILE, None)
    if dados is None:
        dados = _cardapio_padrao()
        _json_save(CARDAPIO_FILE, dados)
    return _normalizar_cardapio(dados)


def db_cardapio_salvar(cardapio: list) -> None:
    # Persiste o cardápio completo.
    cardapio = _normalizar_cardapio(cardapio)
    if _MONGO_OK:
        _mongo_db["cardapio"].drop()
        if cardapio:
            _mongo_db["cardapio"].insert_many(
                [{k: v for k, v in g.items()} for g in cardapio])
    else:
        _json_save(CARDAPIO_FILE, cardapio)


def _cardapio_padrao() -> list:
    #Retorna uma cópia profunda do CARDAPIO embutido no código.
    return copy.deepcopy(CARDAPIO)


def _seed_cardapio_db() -> list:
    #Semeia o cardápio padrão no MongoDB e retorna a lista.
    dados = _cardapio_padrao()
    db_cardapio_salvar(dados)
    return dados

def _normalizar_cardapio(cardapio) -> list:
    #Garante que o cardapio tenha o formato esperado pela interface.
    if not isinstance(cardapio, list):
        return []

    normalizado = []
    for grupo in cardapio:
        if not isinstance(grupo, dict):
            continue

        categoria = str(grupo.get("categoria") or "Sem categoria").strip()
        itens = grupo.get("itens", [])
        if not isinstance(itens, list):
            itens = []

        itens_ok = []
        for item in itens:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("nome") or "").strip()
            if not nome:
                continue
            try:
                preco = round(float(item.get("preco", 0)), 2)
            except (TypeError, ValueError):
                preco = 0
            cor = str(item.get("cor") or "#374151").strip()
            if not re.match(r"^#[0-9A-Fa-f]{6}$", cor):
                cor = "#374151"

            itens_ok.append({
                "nome": nome,
                "preco": preco,
                "tempo": str(item.get("tempo") or "-"),
                "disponivel": bool(item.get("disponivel", True)),
                "cor": cor,
                "ingredientes": item.get("ingredientes") if isinstance(item.get("ingredientes"), list) else [],
                "modo": item.get("modo") if isinstance(item.get("modo"), list) else [],
            })

        normalizado.append({"categoria": categoria or "Sem categoria", "itens": itens_ok})

    return normalizado


# ── USUÁRIOS ───────────────────────────────────────────────────────────────────

def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def carregar_usuarios() -> dict:
    if _MONGO_OK:
        docs = list(_mongo_db["usuarios"].find({}, {"_id": 0}))
        return {d["email"]: d for d in docs}
    return _json_load(USUARIOS_FILE, {})


def salvar_usuarios(usuarios: dict) -> None:
    if _MONGO_OK:
        for email, dados in usuarios.items():
            _mongo_db["usuarios"].update_one(
                {"email": email}, {"$set": {**dados, "email": email}}, upsert=True)
    else:
        _json_save(USUARIOS_FILE, usuarios)


def autenticar(email: str, senha: str):
    usuarios = carregar_usuarios()
    u = usuarios.get(email.lower().strip())
    if u and u.get("hash_senha") == _hash_senha(senha):
        return u
    return None


def is_admin(email: str) -> bool:
    usuarios = carregar_usuarios()
    return usuarios.get(email.lower().strip(), {}).get("perfil") == PERFIL_ADMIN


def cadastrar_usuario(email, senha, nome, perfil=PERFIL_ATENDENTE):
    email = email.lower().strip()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return False, "Informe um e-mail valido."
    if len(senha) < 6:
        return False, "A senha deve ter ao menos 6 caracteres."
    if not nome.strip():
        return False, "Informe o nome do funcionario."
    usuarios = carregar_usuarios()
    if email in usuarios:
        return False, "Este e-mail ja esta cadastrado."
    usuarios[email] = {"hash_senha": _hash_senha(senha),
                       "nome": nome.strip(), "perfil": perfil}
    salvar_usuarios(usuarios)
    return True, "Conta criada com sucesso!"


def remover_usuario(email_alvo, email_admin):
    email_alvo = email_alvo.lower().strip()
    if email_alvo == email_admin.lower().strip():
        return False, "Voce nao pode remover a sua propria conta."
    if _MONGO_OK:
        res = _mongo_db["usuarios"].delete_one({"email": email_alvo})
        return (True, "Conta removida.") if res.deleted_count else (False, "Usuario nao encontrado.")
    usuarios = carregar_usuarios()
    if email_alvo not in usuarios:
        return False, "Usuario nao encontrado."
    del usuarios[email_alvo]
    salvar_usuarios(usuarios)
    return True, "Conta removida com sucesso."


# ============================================================================
# BOOTSTRAP (primeira execução)
# ============================================================================
def _bootstrap():
    os.makedirs(DATA_DIR, exist_ok=True)

    # .gitignore
    gi_entries = ["# === SGCP — nao versionar ===", "data/", "*.json", "*.env", ""]
    if not os.path.exists(GITIGNORE_FILE):
        with open(GITIGNORE_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(gi_entries))

    # data/.env — usuário edita MONGO_URI aqui para ativar MongoDB
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write("# ============================================================\n")
            f.write("# SGCP — Variaveis de Ambiente  (NAO versionar este arquivo)\n")
            f.write("# ============================================================\n")
            f.write("#\n")
            f.write("# COMO CONECTAR AO MONGODB:\n")
            f.write("#   1. Instale o driver:  pip install pymongo\n")
            f.write("#   2. Defina MONGO_URI abaixo (remova o # da linha)\n")
            f.write("#   3. Reinicie o sistema\n")
            f.write("#\n")
            f.write("# Exemplos de URI:\n")
            f.write("#   Local:  mongodb://localhost:27017\n")
            f.write("#   Atlas:  mongodb+srv://usuario:senha@cluster.mongodb.net\n")
            f.write("#\n")
            f.write("# MONGO_URI=mongodb://localhost:27017\n")
            f.write("# MONGO_DB=sgcp\n")
            f.write("#\n")
            f.write("APP_NAME=S.G.C.P\n")
            f.write("APP_VERSION=1.0\n")
            f.write(f"DATA_DIR={DATA_DIR}\n")

    # usuários padrão (só JSON local; MongoDB é semeado na primeira conexão)
    if not _MONGO_OK and not os.path.exists(USUARIOS_FILE):
        _json_save(USUARIOS_FILE, {
            "admin@guanambusiness.com": {
                "hash_senha": _hash_senha("admin123"),
                "nome": "Administrador", "perfil": PERFIL_ADMIN},
            "atendente@guanambusiness.com": {
                "hash_senha": _hash_senha("123456"),
                "nome": "Atendente Padrao", "perfil": PERFIL_ATENDENTE},
        })

    # pedidos iniciais de demonstração (só se não houver nada salvo)
    if not _MONGO_OK and not os.path.exists(PEDIDOS_FILE):
        agora_h = datetime.now().hour
        def hm(delta): return f"{(agora_h - delta) % 24:02d}:{random.randint(0,59):02d}"
        demo = [

        ]
        _json_save(PEDIDOS_FILE, demo)


# ============================================================================
# CARDÁPIO
# ============================================================================

CARDAPIO = [
]

# ============================================================================
# HELPERS — CARDÁPIO / TEMPO MÉDIO
# ============================================================================
_CARDAPIO_IDX = None

def _indice_cardapio() -> dict:
    idx = {}
    for grupo in CARDAPIO:
        for item in grupo["itens"]:
            idx[item["nome"]] = item
    return idx

def _tempo_para_minutos(s: str) -> int:
    try:
        return int(s.split()[0])
    except Exception:
        return 0

def calcular_tempo_medio(itens_pedido: list) -> str:
    global _CARDAPIO_IDX
    if _CARDAPIO_IDX is None:
        _CARDAPIO_IDX = _indice_cardapio()
    tempos = [_tempo_para_minutos(d["tempo"])
              for e in itens_pedido
              if (d := _CARDAPIO_IDX.get(e["nome"])) and d.get("tempo")]
    if not tempos:
        return ""
    return f"~{round(sum(tempos)/len(tempos))} min"


# ============================================================================
# HELPERS — MESAS OCUPADAS
# ============================================================================
def mesas_ocupadas(pedidos: list) -> set:
    #Retorna o conjunto de números de mesa que estão ocupadas (pedido ativo E mesa_liberada=False).
    ocupadas = set()
    for p in pedidos:
        if p.get("status") in ("Aguardando", "Em preparo") and not p.get("mesa_liberada", False):
            ocupadas.add(p["mesa"])
    return ocupadas


# ============================================================================
# HELPERS — GRÁFICOS DINÂMICOS
# ============================================================================
def _calcular_fluxo(pedidos: list):
    #Agrupa pedidos por hora de início → retorna (labels, valores)
    #com as 6 horas mais recentes que tenham pelo menos 1 pedido,
    #mais eventuais horas intermediárias sem pedido para manter continuidade.
    contagem: dict[int, int] = defaultdict(int)
    for p in pedidos:
        try:
            hora = int(p["inicio"].split(":")[0])
            contagem[hora] += 1
        except Exception:
            pass

    if not contagem:
        h = datetime.now().hour
        return ([f"{(h-i)%24:02d}h" for i in range(5, -1, -1)], [0]*6)

    horas_com = sorted(contagem.keys())
    h_min, h_max = horas_com[0], horas_com[-1]
    # preenche horas sem pedido no intervalo
    todas = list(range(h_min, h_max + 1))
    # limita a 6 horas (as últimas)
    if len(todas) > 6:
        todas = todas[-6:]
    labels  = [f"{h:02d}h" for h in todas]
    valores = [contagem.get(h, 0) for h in todas]
    return labels, valores


def _calcular_vendas(pedidos: list):
    #Agrupa faturamento por hora → retorna valores por hora
    #no mesmo intervalo que _calcular_fluxo.
    fat: dict[int, float] = defaultdict(float)
    for p in pedidos:
        try:
            hora = int(p["inicio"].split(":")[0])
            fat[hora] += p.get("total", 0)
        except Exception:
            pass

    if not fat:
        return [0] * 6

    # usa exatamente as mesmas horas que _calcular_fluxo
    labels, _ = _calcular_fluxo(pedidos)
    return [round(fat.get(int(l.replace("h", "")), 0)) for l in labels]


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


def set_theme(name: str) -> None:
    """Alterna entre 'light' e 'dark'. Atualiza COLORS in-place."""
    global CURRENT_THEME
    CURRENT_THEME = name
    COLORS.update(_LIGHT if name == "light" else _DARK)
    try:
        os.makedirs(os.path.dirname(_THEME_FILE), exist_ok=True)
        _json_save(_THEME_FILE, {"theme": name})
    except Exception:
        pass


def load_theme() -> None:
    """Carrega o tema salvo em disco (chamado no início)."""
    try:
        data = _json_load(_THEME_FILE, {"theme": "light"})
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
# PALETA / FONTE / STATUS
# ============================================================================
FONT = "Segoe UI"

STATUS_CORES = {
    "Em preparo": (COLORS["amber"], COLORS["amber_light"]),
    "Finalizado": (COLORS["green"], COLORS["green_light"]),
    "Aguardando": (COLORS["blue"],  COLORS["blue_light"]),
    "Cancelado":  (COLORS["red"],   COLORS["red_light"]),
}


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


# ============================================================================
# APLICAÇÃO PRINCIPAL
# ============================================================================
class SGCPApp(tk.Tk):
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

        # Bootstrap, MongoDB e tema salvo
        _inicializar_mongo()
        _bootstrap()
        load_theme()
        self.configure(bg=COLORS["bg"])

        # carrega cardápio dinâmico (do banco ou JSON) e indexa
        global CARDAPIO, _CARDAPIO_IDX
        CARDAPIO = db_cardapio_carregar()
        _CARDAPIO_IDX = _indice_cardapio()

        # carrega pedidos do banco
        self.pedidos = db_pedidos_carregar()
        self.os_counter = self._proximo_os()

        self.usuario_logado = None
        self.usuario_nome   = None
        self._admin_cache   = None      # cache do perfil — invalida no logout
        self.filtro_status  = tk.StringVar(value="Todos")
        self._ultimo_hash   = None      # hash dos pedidos p/ evitar re-render

        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)
        self.tela_atual = None
        self.mostrar_login()
        self._tick()

    # ── utilitários ──────────────────────────────────────────────────────────

    def _proximo_os(self) -> int:
        nums = []
        for p in self.pedidos:
            try:
                nums.append(int(p["os"].split("-")[1]))
            except Exception:
                pass
        return max(nums, default=1042) + 1

    def limpar_container(self):
        for w in self.container.winfo_children():
            w.destroy()

    def navegar(self, tela):
        if self.tela_atual == tela:
            return
        self.tela_atual = tela
        self._render_tela(tela)

    def _render_tela(self, tela: str):
        try:
            self.attributes("-alpha", 1.0)
        except Exception:
            pass
        if   tela == "home":     self.mostrar_dashboard()
        elif tela == "pedidos":  self.mostrar_pedidos()
        elif tela == "cardapio": self.mostrar_cardapio()

    def _tick(self):
        #Tick a cada 15s: recarrega pedidos e atualiza dashboard só se mudou.
        novos = db_pedidos_carregar()
        novo_hash = hash(json.dumps(
            [{"os":p.get("os"),"status":p.get("status"),"mesa_liberada":p.get("mesa_liberada")}
             for p in novos], sort_keys=True))
        dados_mudaram = (novo_hash != self._ultimo_hash)
        self.pedidos = novos
        self._ultimo_hash = novo_hash
        if self.tela_atual == "home" and dados_mudaram:
            self.mostrar_dashboard()
        self.after(15000, self._tick)

    # ── layout base ──────────────────────────────────────────────────────────

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

    def _montar_menu_inferior(self, root):
        tk.Frame(root, bg=COLORS["gray_light"], height=1).pack(fill="x", side="bottom")
        bar = tk.Frame(root, bg=COLORS["card"], height=68)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        for key, label, icon in [("home", "Início", "⌂"),
                                  ("pedidos", "Pedidos", "≡"),
                                  ("cardapio", "Cardápio", "▤")]:
            ativo = self.tela_atual == key
            cor   = COLORS["green"] if ativo else COLORS["gray"]
            cell  = tk.Frame(bar, bg=COLORS["card"], cursor="hand2")
            cell.pack(side="left", fill="both", expand=True)

            # barra indicadora ativa
            ind = tk.Frame(cell, bg=COLORS["green"] if ativo else COLORS["card"], height=3)
            ind.pack(fill="x")
            ic = tk.Label(cell, text=icon, bg=COLORS["card"], fg=cor,
                          font=(FONT, 18 if ativo else 16))
            ic.pack(pady=(5, 0))
            tx = tk.Label(cell, text=label, bg=COLORS["card"], fg=cor,
                          font=(FONT, 8, "bold" if ativo else "normal"))
            tx.pack()

            def _nav(e, k=key): self.navegar(k)
            for w in (cell, ind, ic, tx):
                w.bind("<Button-1>", _nav)
                w.bind("<Enter>", lambda e, ws=(cell,ind,ic,tx):
                       [x.config(bg=COLORS["gray_light"]) for x in ws])
                w.bind("<Leave>", lambda e, ws=(cell,ind,ic,tx):
                       [x.config(bg=COLORS["card"]) for x in ws])

    # =========================================================================
    # LOGIN
    # =========================================================================
    def mostrar_login(self):
        self.tela_atual = "login"
        self.limpar_container()
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
        modo_txt = "MongoDB" if _MONGO_OK else "JSON local"
        modo_cor = COLORS["green"] if _MONGO_OK else COLORS["amber"]
        tk.Label(wrap, text=f"v1.0  \u2014  {modo_txt}", bg=COLORS["dark"],
                 fg=modo_cor, font=(FONT, 8)).pack(side="bottom", pady=12)

    def _validar_login(self):
        email = self.entry_email.get().strip()
        senha = self.entry_senha.get().strip()
        def _show_err(msg):
            try: self._login_status.config(text=msg, fg=COLORS["red"])
            except Exception: pass

        if not email or "@" not in email:
            _show_err("Informe um e-mail valido."); return
        if len(senha) < 6:
            _show_err("Senha com ao menos 6 caracteres."); return

        # Feedback visual de carregamento
        try: self._btn_login.config(text="Verificando...", cursor="watch")
        except Exception: pass
        self.update_idletasks()

        u = autenticar(email, senha)
        try: self._btn_login.config(text="Entrar", cursor="hand2")
        except Exception: pass

        if u is None:
            _show_err("E-mail ou senha incorretos.")
            return
        self.usuario_logado = email
        self.usuario_nome   = u.get("nome", email)
        self._admin_cache   = (u.get("perfil") == PERFIL_ADMIN)
        self._ultimo_hash   = None  # força refresh no próximo tick
        self.navegar("home")

    def _is_admin(self) -> bool:
        """is_admin com cache de sessão — evita re-ler o banco a cada widget."""
        if self._admin_cache is None:
            self._admin_cache = self._is_admin() if self.usuario_logado else False
        return self._admin_cache

    def _logout(self):
        if messagebox.askyesno("Sair", "Deseja encerrar a sessao?"):
            self.usuario_logado = None
            self.usuario_nome   = None
            self._admin_cache   = None
            self.mostrar_login()

    # =========================================================================
    # DASHBOARD
    # =========================================================================
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
        db_txt = "MongoDB" if _MONGO_OK else "JSON local"
        db_bg  = COLORS["green_light"] if _MONGO_OK else COLORS["amber_light"]
        db_fg  = COLORS["green_dark"]  if _MONGO_OK else COLORS["amber"]
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
        frames = 24
        def _step(i=1):
            if not cv.winfo_exists(): return
            t = i / frames
            ext = target_ext * t
            pct_now = abs(ext) / 360
            cv.itemconfig(arc_id, extent=ext)
            cv.itemconfig(pct_lbl, text=f"{int(pct_now*100)}%")
            if i < frames:
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

    # =========================================================================
    # GESTÃO DE PEDIDOS
    # =========================================================================
    def mostrar_pedidos(self):
        self.tela_atual = "pedidos"
        self.limpar_container()
        body = self._montar_layout("Pedidos", "Ordens de Servico (O.S.)")
        pad  = tk.Frame(body, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=16, pady=16)

        # busca
        bc = tk.Frame(pad, bg=COLORS["card"],
                      highlightbackground=COLORS["gray_light"], highlightthickness=1)
        bc.pack(fill="x")
        br = tk.Frame(bc, bg=COLORS["card"])
        br.pack(fill="x", padx=12, pady=10)
        tk.Label(br, text="\u26B2", bg=COLORS["card"], fg=COLORS["gray"],
                 font=(FONT,13)).pack(side="left")
        self.entry_busca = tk.Entry(br, font=(FONT,11), relief="flat",
                                    bg=COLORS["card"], fg=COLORS["dark"])
        self.entry_busca.pack(side="left", fill="x", expand=True, padx=8)
        self.entry_busca.bind("<KeyRelease>", lambda e: self._render_lista_pedidos())

        # chips de filtro
        self.chips_frame = tk.Frame(pad, bg=COLORS["bg"])
        self.chips_frame.pack(fill="x", pady=(12, 4))
        for opt in ["Todos", "Aguardando", "Em preparo", "Finalizado"]:
            self._chip_filtro(self.chips_frame, opt)

        self.lista_pedidos_frame = tk.Frame(pad, bg=COLORS["bg"])
        self.lista_pedidos_frame.pack(fill="both", expand=True, pady=(8,0))
        self._render_lista_pedidos()

        HoverButton(pad, "+ Novo Pedido", command=self.abrir_novo_pedido,
                    font_size=12).pack(fill="x", pady=(16,8))

    def _chip_filtro(self, parent, opt):
        ativo = self.filtro_status.get() == opt
        chip = tk.Label(parent, text=opt,
                        bg=COLORS["green"] if ativo else COLORS["card"],
                        fg=COLORS["white"] if ativo else COLORS["gray"],
                        font=(FONT,9,"bold"), padx=12, pady=6, cursor="hand2",
                        highlightbackground=COLORS["gray_light"],
                        highlightthickness=0 if ativo else 1)
        chip.pack(side="left", padx=(0,6))
        chip.bind("<Button-1>", lambda e, o=opt: self._set_filtro(o))
        chip.bind("<Enter>", lambda e, c=chip, a=ativo:
                  c.config(bg=COLORS["green_dark"] if a else COLORS["gray_light"]))
        chip.bind("<Leave>", lambda e, c=chip, a=ativo:
                  c.config(bg=COLORS["green"] if a else COLORS["card"]))

    def _set_filtro(self, opt):
        self.filtro_status.set(opt)
        # Atualiza apenas os chips e a lista, sem recriar a página toda
        for w in self.chips_frame.winfo_children():
            w.destroy()
        for o in ["Todos", "Aguardando", "Em preparo", "Finalizado"]:
            self._chip_filtro(self.chips_frame, o)
        self._render_lista_pedidos()

    def _render_lista_pedidos(self):
        for w in self.lista_pedidos_frame.winfo_children():
            w.destroy()
        termo  = self.entry_busca.get().strip().lower()
        filtro = self.filtro_status.get()
        count  = 0
        for p in self.pedidos:
            if filtro != "Todos" and p["status"] != filtro:
                continue
            alvo = f"{p['os']} mesa {p['mesa']} {p['status']}".lower()
            if termo and termo not in alvo:
                continue
            count += 1
            self._card_pedido(self.lista_pedidos_frame, p)
        if count == 0:
            tk.Label(self.lista_pedidos_frame,
                     text="Nenhum pedido encontrado.",
                     bg=COLORS["bg"], fg=COLORS["gray"], font=(FONT,10)).pack(pady=20)

    def _card_pedido(self, parent, p):
        mesa_lib = p.get("mesa_liberada", False)
        card = tk.Frame(parent, bg=COLORS["card"],
                        highlightbackground=COLORS["gray_light"], highlightthickness=1)
        card.pack(fill="x", pady=5)
        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill="x", padx=14, pady=12)

        # linha 1: mesa + badge liberada + status
        top = tk.Frame(inner, bg=COLORS["card"])
        top.pack(fill="x")
        mesa_bg = COLORS["gray"] if mesa_lib else COLORS["dark"]
        tk.Label(tk.Frame(top, bg=mesa_bg),
                 text=f"Mesa {p['mesa']:02d}", bg=mesa_bg,
                 fg=COLORS["white"], font=(FONT,10,"bold"),
                 padx=10, pady=4).pack()
        top.winfo_children()[0].pack(side="left")
        if mesa_lib:
            tk.Label(top, text="LIBERADA", bg=COLORS["gray_light"],
                     fg=COLORS["gray"], font=(FONT,7,"bold"),
                     padx=6, pady=2).pack(side="left", padx=(6,0))
        fg_s, bg_s = STATUS_CORES.get(p["status"],(COLORS["gray"],COLORS["gray_light"]))
        tk.Label(top, text=p["status"], bg=bg_s, fg=fg_s,
                 font=(FONT,9,"bold"), padx=10, pady=4).pack(side="right")

        # linha 2: OS + itens + total
        det = tk.Frame(inner, bg=COLORS["card"])
        det.pack(fill="x", pady=(10,0))
        tk.Label(det, text=p["os"], bg=COLORS["card"], fg=COLORS["dark"],
                 font=(FONT,12,"bold")).pack(side="left")
        tk.Label(det, text=f"  \u2014  {p['itens']} iten(s)",
                 bg=COLORS["card"], fg=COLORS["gray"], font=(FONT,9)).pack(side="left")
        tk.Label(det, text=brl(p["total"]), bg=COLORS["card"],
                 fg=COLORS["green"], font=(FONT,11,"bold")).pack(side="right")

        # linha 3: tempo médio
        if p["status"] in ("Aguardando","Em preparo") and not mesa_lib:
            ts = calcular_tempo_medio(p.get("itens_lista",[]))
            if ts:
                tr = tk.Frame(inner, bg=COLORS["card"])
                tr.pack(fill="x", pady=(4,0))
                tbg = COLORS["amber_light"] if p["status"]=="Em preparo" else COLORS["blue_light"]
                tfg = COLORS["amber"]       if p["status"]=="Em preparo" else COLORS["blue"]
                tk.Label(tr, text=f"\u23F3  Tempo medio de preparo: {ts}",
                         bg=tbg, fg=tfg, font=(FONT,8,"bold"),
                         padx=8, pady=3).pack(anchor="w")

        # linha 4: rodapé
        rod = tk.Frame(inner, bg=COLORS["card"])
        rod.pack(fill="x", pady=(8,0))
        tk.Label(rod, text=f"\u23F1  Inicio {p['inicio']}",
                 bg=COLORS["card"], fg=COLORS["gray"], font=(FONT,9)).pack(side="left")

        # botão Ver OS
        HoverButton(rod, "Ver OS",
                    command=lambda pp=p: self._abrir_detalhe_os(pp),
                    bg=COLORS["blue_light"], fg=COLORS["blue"],
                    hover_bg=COLORS["blue"], font_size=8,
                    padx=10, pady=4).pack(side="right", padx=(6,0))

        # botão Desocupar Mesa
        if p["status"] in ("Finalizado","Em preparo","Aguardando") and not mesa_lib:
            HoverButton(rod, "Desocupar",
                        command=lambda pp=p: self._desocupar_mesa(pp),
                        bg=COLORS["purple_light"], fg=COLORS["purple"],
                        hover_bg=COLORS["purple"], font_size=8,
                        padx=10, pady=4).pack(side="right", padx=(6,0))

        # botão Avançar status
        if p["status"] not in ("Finalizado","Cancelado"):
            HoverButton(rod, "Avan\u00e7ar",
                        command=lambda pp=p: self._avancar_status(pp),
                        bg=COLORS["green_light"], fg=COLORS["green_dark"],
                        hover_bg=COLORS["green"], font_size=8,
                        padx=10, pady=4).pack(side="right")

    def _avancar_status(self, p):
        fluxo = {"Aguardando":"Em preparo","Em preparo":"Finalizado"}
        novo  = fluxo.get(p["status"], p["status"])
        p["status"] = novo
        db_pedido_atualizar_campo(p["os"], "status", novo)
        self.mostrar_pedidos()

    def _desocupar_mesa(self, p):
        if not messagebox.askyesno(
                "Desocupar Mesa",
                f"Deseja liberar a Mesa {p['mesa']:02d}?\n"
                f"A OS {p['os']} sera mantida nos registros."):
            return
        p["mesa_liberada"] = True
        db_pedido_atualizar_campo(p["os"], "mesa_liberada", True)
        messagebox.showinfo(
            "Mesa liberada",
            f"Mesa {p['mesa']:02d} desocupada com sucesso.\n"
            f"OS {p['os']} registrada no historico.")
        # Recarrega pedidos do banco para garantir consistência
        self.pedidos = db_pedidos_carregar()
        # Navega para home para que o gráfico de ocupação atualize imediatamente
        self.navegar("home")

    # =========================================================================
    # DETALHE DA OS
    # =========================================================================
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

    # =========================================================================
    # GERENCIAR USUÁRIOS (admin)
    # =========================================================================
    def _abrir_gerenciar_usuarios(self):
        if not self._is_admin():
            messagebox.showerror("Acesso negado",
                                 "Apenas o Administrador pode gerenciar contas.")
            return
        win = tk.Toplevel(self)
        win.title("Gerenciar Usuarios")
        win.geometry("420x680")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self); win.grab_set()

        head = tk.Frame(win, bg=COLORS["dark"], height=64)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text="Gerenciar Usuarios", bg=COLORS["dark"],
                 fg=COLORS["white"], font=(FONT,14,"bold")).pack(side="left",padx=20,pady=18)
        tk.Label(head, text="  ADMIN  ", bg=COLORS["green"],
                 fg=COLORS["white"], font=(FONT,8,"bold"),
                 padx=6, pady=2).pack(side="right", padx=18)

        bw = tk.Frame(win, bg=COLORS["bg"])
        bw.pack(fill="both", expand=True)
        cg = tk.Canvas(bw, bg=COLORS["bg"], highlightthickness=0)
        sg = ttk.Scrollbar(bw, orient="vertical", command=cg.yview)
        sf = tk.Frame(cg, bg=COLORS["bg"])
        sf.bind("<Configure>", lambda e: cg.configure(scrollregion=cg.bbox("all")))
        wi = cg.create_window((0,0), window=sf, anchor="nw")
        cg.bind("<Configure>", lambda e: cg.itemconfig(wi, width=e.width))
        cg.configure(yscrollcommand=sg.set)
        cg.pack(side="left", fill="both", expand=True)
        sg.pack(side="right", fill="y")

        pad = tk.Frame(sf, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=16, pady=16)

        lista_f = tk.Frame(pad, bg=COLORS["bg"])
        lista_f.pack(fill="x")

        def _render():
            for w in lista_f.winfo_children(): w.destroy()
            tk.Label(lista_f, text="Usuarios cadastrados",
                     bg=COLORS["bg"], fg=COLORS["dark"],
                     font=(FONT,12,"bold")).pack(anchor="w", pady=(0,8))
            for email_u, dados in carregar_usuarios().items():
                cu = tk.Frame(lista_f, bg=COLORS["card"],
                              highlightbackground=COLORS["gray_light"], highlightthickness=1)
                cu.pack(fill="x", pady=4)
                ru = tk.Frame(cu, bg=COLORS["card"])
                ru.pack(fill="x", padx=12, pady=10)
                p = dados.get("perfil", PERFIL_ATENDENTE)
                pbg = COLORS["green"] if p==PERFIL_ADMIN else COLORS["blue"]
                tk.Label(ru, text=p.upper(), bg=pbg, fg=COLORS["white"],
                         font=(FONT,8,"bold"), padx=6, pady=2).pack(side="left",padx=(0,10))
                iu = tk.Frame(ru, bg=COLORS["card"])
                iu.pack(side="left", fill="x", expand=True)
                tk.Label(iu, text=dados.get("nome","—"), bg=COLORS["card"],
                         fg=COLORS["dark"], font=(FONT,10,"bold")).pack(anchor="w")
                tk.Label(iu, text=email_u, bg=COLORS["card"],
                         fg=COLORS["gray"], font=(FONT,8)).pack(anchor="w")
                if email_u != self.usuario_logado:
                    def _rem(e=email_u):
                        if messagebox.askyesno("Confirmar",f"Remover {e}?",parent=win):
                            ok, msg = remover_usuario(e, self.usuario_logado)
                            (messagebox.showinfo if ok else messagebox.showerror)(
                                "Resultado", msg, parent=win)
                            if ok: _render()
                    HoverButton(ru, "Remover", command=_rem,
                                bg=COLORS["red_light"], fg=COLORS["red"],
                                hover_bg=COLORS["red"], font_size=8,
                                padx=8, pady=3).pack(side="right")

        _render()
        tk.Frame(pad, bg=COLORS["gray_light"], height=1).pack(fill="x", pady=(20,16))
        tk.Label(pad, text="Criar nova conta de funcionario",
                 bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT,12,"bold")).pack(anchor="w", pady=(0,10))

        fc = tk.Frame(pad, bg=COLORS["card"],
                      highlightbackground=COLORS["gray_light"], highlightthickness=1)
        fc.pack(fill="x")
        fm = tk.Frame(fc, bg=COLORS["card"])
        fm.pack(padx=16, pady=16, fill="x")

        def _campo_form(lbl, **kw):
            tk.Label(fm, text=lbl, bg=COLORS["card"], fg=COLORS["dark_soft"],
                     font=(FONT,9,"bold")).pack(anchor="w")
            e = tk.Entry(fm, font=(FONT,11), relief="flat",
                         bg=COLORS["bg"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"], **kw)
            e.pack(fill="x", ipady=7, pady=(4,12))
            return e

        fn = _campo_form("Nome completo")
        fe = _campo_form("E-mail")
        fs = _campo_form("Senha (minimo 6 caracteres)", show="*")
        fc2= _campo_form("Confirmar senha", show="*")
        tk.Label(fm, text="Perfil de acesso", bg=COLORS["card"],
                 fg=COLORS["dark_soft"], font=(FONT,9,"bold")).pack(anchor="w")
        pv = tk.StringVar(value=PERFIL_ATENDENTE)
        pf = tk.Frame(fm, bg=COLORS["card"]); pf.pack(fill="x", pady=(4,12))
        for val, lbl_p in [(PERFIL_ATENDENTE,"Atendente"),(PERFIL_ADMIN,"Administrador")]:
            tk.Radiobutton(pf, text=lbl_p, variable=pv, value=val,
                           bg=COLORS["card"], fg=COLORS["dark_soft"],
                           selectcolor=COLORS["green_light"],
                           font=(FONT,10), activebackground=COLORS["card"]
                           ).pack(side="left", padx=(0,16))

        def _criar():
            s, c = fs.get().strip(), fc2.get().strip()
            if s != c:
                messagebox.showerror("Erro","As senhas nao conferem.",parent=win); return
            ok, msg = cadastrar_usuario(fe.get().strip(), s, fn.get().strip(), pv.get())
            (messagebox.showinfo if ok else messagebox.showerror)("Resultado",msg,parent=win)
            if ok:
                for e in (fn,fe,fs,fc2): e.delete(0,tk.END)
                pv.set(PERFIL_ATENDENTE); _render()

        HoverButton(fm, "Criar conta", command=_criar, font_size=11).pack(fill="x")
        fc2.bind("<Return>", lambda e: _criar())

        HoverButton(win, "Fechar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=16, pady=12)

    # =========================================================================
    # CARDÁPIO
    # =========================================================================
    def _reload_cardapio(self):
        """Recarrega CARDAPIO do banco e reindexia. Chamado após qualquer edição."""
        global CARDAPIO, _CARDAPIO_IDX
        CARDAPIO = db_cardapio_carregar()
        _CARDAPIO_IDX = _indice_cardapio()

    def mostrar_cardapio(self):
        self.tela_atual = "cardapio"
        self.limpar_container()
        admin = self._is_admin()
        subtitulo = "Pratos e bebidas  —  Modo Admin" if admin                     else "Pratos e bebidas  —  Somente visualizacao"
        body = self._montar_layout("Cardapio", subtitulo)
        pad  = tk.Frame(body, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=16, pady=16)

        # Botões de ação admin — somente admin
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

        # Badge modo atendente
        if not admin:
            tk.Label(pad,
                     text="Modo visualizacao  —  Apenas o Administrador pode editar o cardapio.",
                     bg=COLORS["amber_light"], fg=COLORS["amber"],
                     font=(FONT, 8), padx=10, pady=6,
                     wraplength=360, justify="left").pack(
                         fill="x", pady=(0, 12))

        for grupo in CARDAPIO:
            # cabeçalho da categoria
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
                            font_size=8, padx=10, pady=4).pack(
                                side="right")
            for item in grupo["itens"]:
                self._card_item_cardapio(pad, item, admin=admin)

    def _card_item_cardapio(self, parent, item, admin=False):
        card = tk.Frame(parent, bg=COLORS["card"],
                        highlightbackground=COLORS["gray_light"],
                        highlightthickness=1)
        card.pack(fill="x", pady=5)
        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill="x", padx=12, pady=12)

        # avatar colorido
        img = tk.Canvas(inner, width=56, height=56, bg=COLORS["card"],
                        highlightthickness=0, cursor="hand2")
        img.pack(side="left")
        img.create_rectangle(0, 0, 56, 56, fill=item["cor"], outline="")
        img.create_text(28, 28, text=item["nome"][0],
                        fill=COLORS["white"], font=(FONT, 20, "bold"))

        # info central
        info = tk.Frame(inner, bg=COLORS["card"])
        info.pack(side="left", fill="x", expand=True, padx=10)
        tk.Label(info, text=item["nome"], bg=COLORS["card"], fg=COLORS["dark"],
                 font=(FONT, 10, "bold"), anchor="w",
                 justify="left", wraplength=160).pack(anchor="w")
        row_preco = tk.Frame(info, bg=COLORS["card"])
        row_preco.pack(anchor="w", fill="x")
        tk.Label(row_preco, text=brl(item["preco"]), bg=COLORS["card"],
                 fg=COLORS["green"], font=(FONT, 10, "bold")).pack(side="left")
        tk.Label(row_preco, text=f"  ⏱ {item.get('tempo','—')}",
                 bg=COLORS["card"], fg=COLORS["gray"],
                 font=(FONT, 8)).pack(side="left")
        disp_bg = COLORS["green_light"] if item["disponivel"] else COLORS["red_light"]
        disp_fg = COLORS["green_dark"]  if item["disponivel"] else COLORS["red"]
        tk.Label(info, text="Disponivel" if item["disponivel"] else "Indisponivel",
                 bg=disp_bg, fg=disp_fg,
                 font=(FONT, 8, "bold"), padx=8, pady=2).pack(anchor="w", pady=(4, 0))

        # ações à direita
        acao_col = tk.Frame(inner, bg=COLORS["card"])
        acao_col.pack(side="right")

        if admin:
            HoverButton(acao_col, "Editar",
                        command=lambda it=item: self._abrir_form_receita(it),
                        bg=COLORS["amber_light"], fg=COLORS["amber"],
                        hover_bg=COLORS["amber"], font_size=8,
                        padx=8, pady=3).pack(pady=(0, 4))

        # seta "ver ficha" sempre visível
        seta = tk.Label(acao_col, text="›", bg=COLORS["card"],
                        fg=COLORS["gray"], font=(FONT, 18, "bold"),
                        cursor="hand2")
        seta.pack()
        for w in (img, seta):
            w.bind("<Button-1>", lambda e, it=item: self._abrir_ficha_tecnica(it))
        img.bind("<Button-1>", lambda e, it=item: self._abrir_ficha_tecnica(it))

    def _abrir_ficha_tecnica(self, item):
        admin = self._is_admin()
        win = tk.Toplevel(self)
        win.title("Ficha Tecnica")
        win.geometry("400x660")
        win.configure(bg=COLORS["bg"])
        win.resizable(False, False)
        win.transient(self); win.grab_set()

        # Cabeçalho colorido
        head = tk.Frame(win, bg=item["cor"], height=120)
        head.pack(fill="x"); head.pack_propagate(False)
        hrow = tk.Frame(head, bg=item["cor"])
        hrow.pack(fill="x", padx=20, pady=(24, 0))
        tk.Label(hrow, text=item["nome"], bg=item["cor"], fg=COLORS["white"],
                 font=(FONT, 15, "bold"), wraplength=260,
                 justify="left").pack(side="left", anchor="w")
        if admin:
            HoverButton(hrow, "✎ Editar",
                        command=lambda: [win.destroy(),
                                         self._abrir_form_receita(item)],
                        bg=COLORS["white"], fg=item["cor"],
                        hover_bg=COLORS["gray_light"],
                        font_size=9, padx=10, pady=4).pack(
                            side="right", anchor="n")
        tk.Label(head, text=brl(item["preco"]), bg=item["cor"],
                 fg=COLORS["white"], font=(FONT, 12)).pack(anchor="w", padx=20)

        # Corpo com scroll
        wrap = tk.Frame(win, bg=COLORS["bg"])
        wrap.pack(fill="both", expand=True)
        cv_ft = tk.Canvas(wrap, bg=COLORS["bg"], highlightthickness=0)
        sb_ft = ttk.Scrollbar(wrap, orient="vertical", command=cv_ft.yview)
        sf_ft = tk.Frame(cv_ft, bg=COLORS["bg"])
        sf_ft.bind("<Configure>",
                   lambda e: cv_ft.configure(scrollregion=cv_ft.bbox("all")))
        wid_ft = cv_ft.create_window((0, 0), window=sf_ft, anchor="nw")
        cv_ft.bind("<Configure>",
                   lambda e: cv_ft.itemconfig(wid_ft, width=e.width))
        cv_ft.configure(yscrollcommand=sb_ft.set)
        cv_ft.pack(side="left", fill="both", expand=True)
        sb_ft.pack(side="right", fill="y")
        cv_ft.bind_all("<MouseWheel>",
                       lambda e: cv_ft.yview_scroll(int(-1*(e.delta/120)), "units"))

        body = tk.Frame(sf_ft, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Meta
        meta_card = tk.Frame(body, bg=COLORS["card"],
                             highlightbackground=COLORS["gray_light"],
                             highlightthickness=1)
        meta_card.pack(fill="x", pady=(0, 12))
        meta = tk.Frame(meta_card, bg=COLORS["card"])
        meta.pack(fill="x", padx=14, pady=10)

        def _mrow(lbl, val, vc=COLORS["dark_soft"]):
            r = tk.Frame(meta, bg=COLORS["card"]); r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl, bg=COLORS["card"], fg=COLORS["gray"],
                     font=(FONT, 9)).pack(side="left")
            tk.Label(r, text=val, bg=COLORS["card"], fg=vc,
                     font=(FONT, 9, "bold")).pack(side="right")

        _mrow("Tempo de preparo", item.get("tempo", "—"))
        _mrow("Disponibilidade",
              "Disponivel" if item["disponivel"] else "Indisponivel",
              COLORS["green"] if item["disponivel"] else COLORS["red"])
        _mrow("Categoria", self._categoria_do_item(item["nome"]))

        # Ingredientes
        tk.Label(body, text="Ingredientes", bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(8, 6))
        for ing in item.get("ingredientes", []):
            tk.Label(body, text=f"•  {ing}", bg=COLORS["bg"],
                     fg=COLORS["dark_soft"], font=(FONT, 10),
                     anchor="w", wraplength=340,
                     justify="left").pack(anchor="w", pady=1)

        # Modo de preparo
        tk.Label(body, text="Modo de Preparo", bg=COLORS["bg"], fg=COLORS["dark"],
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(14, 6))
        for i, passo in enumerate(item.get("modo", []), 1):
            linha = tk.Frame(body, bg=COLORS["bg"])
            linha.pack(fill="x", anchor="w", pady=3)
            tk.Label(linha, text=str(i), bg=COLORS["green"], fg=COLORS["white"],
                     font=(FONT, 9, "bold"), width=2).pack(side="left", padx=(0, 8))
            tk.Label(linha, text=passo, bg=COLORS["bg"], fg=COLORS["dark_soft"],
                     font=(FONT, 10), wraplength=310,
                     justify="left").pack(side="left", anchor="w")

        HoverButton(win, "Fechar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"]).pack(
                        fill="x", padx=20, pady=12)

    # =========================================================================
    # HELPERS INTERNOS DO CARDÁPIO
    # =========================================================================
    def _categoria_do_item(self, nome_item: str) -> str:
        for grupo in CARDAPIO:
            for it in grupo["itens"]:
                if it["nome"] == nome_item:
                    return grupo["categoria"]
        return "—"

    # =========================================================================
    # FORMULÁRIO DE RECEITA (criar / editar) — somente admin
    # =========================================================================
    def _abrir_form_receita(self, item=None):
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

        # Cabeçalho
        head = tk.Frame(win, bg=COLORS["dark"], height=64)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text=titulo_win, bg=COLORS["dark"], fg=COLORS["white"],
                 font=(FONT, 14, "bold")).pack(side="left", padx=20, pady=18)
        tk.Label(head, text="ADMIN", bg=COLORS["green"], fg=COLORS["white"],
                 font=(FONT, 8, "bold"), padx=8, pady=3).pack(
                     side="right", padx=18)

        # Corpo com scroll
        wrap = tk.Frame(win, bg=COLORS["bg"])
        wrap.pack(fill="both", expand=True)
        cv_f = tk.Canvas(wrap, bg=COLORS["bg"], highlightthickness=0)
        sb_f = ttk.Scrollbar(wrap, orient="vertical", command=cv_f.yview)
        sf_f = tk.Frame(cv_f, bg=COLORS["bg"])
        sf_f.bind("<Configure>",
                  lambda e: cv_f.configure(scrollregion=cv_f.bbox("all")))
        wid_f = cv_f.create_window((0, 0), window=sf_f, anchor="nw")
        cv_f.bind("<Configure>",
                  lambda e: cv_f.itemconfig(wid_f, width=e.width))
        cv_f.configure(yscrollcommand=sb_f.set)
        cv_f.pack(side="left", fill="both", expand=True)
        sb_f.pack(side="right", fill="y")
        cv_f.bind_all("<MouseWheel>",
                      lambda e: cv_f.yview_scroll(int(-1*(e.delta/120)), "units"))

        pad = tk.Frame(sf_f, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=18, pady=16)

        # ── helper: campo de texto simples ──────────────────────────────────
        def _campo(lbl, val="", show=None):
            tk.Label(pad, text=lbl, bg=COLORS["bg"], fg=COLORS["dark_soft"],
                     font=(FONT, 9, "bold")).pack(anchor="w", pady=(8, 0))
            e = tk.Entry(pad, font=(FONT, 11), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"],
                         highlightthickness=1)
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
            entradas = []

            def _add_linha(texto=""):
                row = tk.Frame(container, bg=COLORS["bg"])
                row.pack(fill="x", pady=2)
                n = tk.Label(row, text=f"{len(entradas)+1}.",
                             bg=COLORS["bg"], fg=COLORS["gray"],
                             font=(FONT, 9), width=2)
                n.pack(side="left", padx=(0, 6))
                e = tk.Entry(row, font=(FONT, 10), relief="flat",
                             bg=COLORS["card"], fg=COLORS["dark"],
                             insertbackground=COLORS["dark"],
                             highlightbackground=COLORS["gray_light"],
                             highlightthickness=1)
                e.pack(side="left", fill="x", expand=True, ipady=5)
                if texto: e.insert(0, texto)

                def _remover(r=row, en=e):
                    entradas.remove(en)
                    r.destroy()
                    # renumera
                    for idx, ef in enumerate(entradas, 1):
                        ef.master.winfo_children()[0].config(text=f"{idx}.")

                btn_rm = tk.Label(row, text="✕", bg=COLORS["bg"],
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
                        font_size=9, padx=10, pady=4).pack(
                            anchor="w", pady=(6, 0))

            def _get_valores():
                return [e.get().strip() for e in entradas if e.get().strip()]

            return _get_valores

        # ── Campos principais ────────────────────────────────────────────────
        f_nome  = _campo("Nome do prato / bebida",
                         item["nome"] if modo_edicao else "")
        f_preco = _campo("Preco (R$)",
                         f"{item['preco']:.2f}".replace(".", ",")
                         if modo_edicao else "")
        f_tempo = _campo("Tempo de preparo (ex: 25 min)",
                         item.get("tempo", "") if modo_edicao else "")

        # Disponibilidade
        tk.Label(pad, text="Disponibilidade", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(
                     anchor="w", pady=(10, 4))
        disp_var = tk.BooleanVar(value=item.get("disponivel", True)
                                 if modo_edicao else True)
        disp_row = tk.Frame(pad, bg=COLORS["bg"])
        disp_row.pack(anchor="w")
        for txt, val in [("Disponivel", True), ("Indisponivel", False)]:
            tk.Radiobutton(disp_row, text=txt, variable=disp_var, value=val,
                           bg=COLORS["bg"], fg=COLORS["dark_soft"],
                           selectcolor=COLORS["green_light"],
                           font=(FONT, 10),
                           activebackground=COLORS["bg"]).pack(
                               side="left", padx=(0, 14))

        # Cor do avatar com preview ao vivo
        tk.Label(pad, text="Cor do avatar (hex, ex: #7C2D12)",
                 bg=COLORS["bg"], fg=COLORS["dark_soft"],
                 font=(FONT, 9, "bold")).pack(anchor="w", pady=(10, 0))
        cor_row = tk.Frame(pad, bg=COLORS["bg"])
        cor_row.pack(fill="x", pady=(4, 0))
        f_cor = tk.Entry(cor_row, font=(FONT, 11), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"],
                         highlightthickness=1)
        f_cor.pack(side="left", fill="x", expand=True, ipady=7)
        preview_cv = tk.Canvas(cor_row, width=40, height=36,
                               bg=COLORS["card"], highlightthickness=0)
        preview_cv.pack(side="left", padx=(6, 0))
        cor_inicial = item.get("cor", "#374151") if modo_edicao else "#374151"
        preview_cv.create_rectangle(0, 0, 40, 36, fill=cor_inicial, outline="")
        preview_cv.create_text(20, 18, text=item["nome"][0].upper()
                               if modo_edicao else "A",
                               fill=COLORS["white"], font=(FONT, 14, "bold"),
                               tags="letra")
        if modo_edicao: f_cor.insert(0, cor_inicial)

        def _atualizar_preview(*_):
            cor = f_cor.get().strip()
            if re.match(r"^#[0-9A-Fa-f]{6}$", cor):
                preview_cv.config(bg=COLORS["card"])
                preview_cv.itemconfig("all", fill=cor)
                # Garante que o texto fique branco sobre qualquer cor
                preview_cv.itemconfig("letra", fill=COLORS["white"])
        f_cor.bind("<KeyRelease>", _atualizar_preview)
        f_cor.bind("<FocusOut>",   _atualizar_preview)

        # Categoria (combo com as existentes + nova)
        cats = [g["categoria"] for g in CARDAPIO]
        if not modo_edicao and cats:
            cat_atual = cats[0]
        elif modo_edicao:
            cat_atual = self._categoria_do_item(item["nome"])
        else:
            cat_atual = ""

        tk.Label(pad, text="Categoria", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(
                     anchor="w", pady=(10, 0))
        cat_var = tk.StringVar(value=cat_atual)
        cat_combo = ttk.Combobox(pad, textvariable=cat_var,
                                 values=cats, font=(FONT, 10))
        cat_combo.pack(fill="x", pady=(4, 0), ipady=4)

        # Listas editáveis
        get_ings  = _lista_editavel(
            "Ingredientes",
            item.get("ingredientes", []) if modo_edicao else [])
        get_modo  = _lista_editavel(
            "Modo de Preparo",
            item.get("modo", []) if modo_edicao else [])

        # ── Separador ────────────────────────────────────────────────────────
        tk.Frame(pad, bg=COLORS["gray_light"], height=1).pack(
            fill="x", pady=(18, 0))

        # ── Botão excluir (somente edição) ───────────────────────────────────
        if modo_edicao:
            def _excluir():
                if not messagebox.askyesno(
                        "Excluir receita",
                        f"Excluir permanentemente '{item['nome']}'?",
                        parent=win):
                    return
                global CARDAPIO
                for grupo in CARDAPIO:
                    grupo["itens"] = [
                        it for it in grupo["itens"]
                        if it["nome"] != item["nome"]]
                # remove grupos vazios
                CARDAPIO = [g for g in CARDAPIO if g["itens"]]
                db_cardapio_salvar(CARDAPIO)
                self._reload_cardapio()
                messagebox.showinfo("Excluido",
                                    f"'{item['nome']}' removido do cardapio.")
                win.destroy()
                self.mostrar_cardapio()

            HoverButton(pad, "⚲  Excluir esta receita",
                        command=_excluir,
                        bg=COLORS["red_light"], fg=COLORS["red"],
                        hover_bg=COLORS["red"],
                        font_size=10).pack(fill="x", pady=(12, 0))

        # ── Botão salvar ─────────────────────────────────────────────────────
        def _salvar():
            global CARDAPIO
            nome   = f_nome.get().strip()
            preco_s= f_preco.get().strip().replace(",", ".")
            tempo  = f_tempo.get().strip()
            cor    = f_cor.get().strip() or "#374151"
            cat    = cat_var.get().strip()
            ings   = get_ings()
            modo_p = get_modo()

            # Validações
            if not nome:
                messagebox.showerror("Erro", "Informe o nome do prato.",
                                     parent=win); return
            try:
                preco = round(float(preco_s), 2)
                if preco <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro",
                                     "Preco invalido. Use ex: 29,90",
                                     parent=win); return
            if not cat:
                messagebox.showerror("Erro", "Selecione ou digite a categoria.",
                                     parent=win); return
            # Impede nomes duplicados ao criar nova receita
            if not modo_edicao:
                todos_nomes = [it["nome"].lower()
                               for g in CARDAPIO for it in g["itens"]]
                if nome.lower() in todos_nomes:
                    messagebox.showerror(
                        "Erro",
                        f"Ja existe uma receita com o nome '{nome}'.",
                        parent=win); return

            # Validar cor hex
            if not re.match(r"^#[0-9A-Fa-f]{6}$", cor):
                cor = "#374151"

            # Normalizar tempo: aceita "25", "25 min", "25min" → "25 min"
            tempo_norm = tempo.strip()
            if tempo_norm:
                m = re.match(r"^(\d+)\s*(min)?$", tempo_norm, re.I)
                tempo_norm = f"{m.group(1)} min" if m else tempo_norm
            else:
                tempo_norm = "—"

            novo_item = {
                "nome":        nome,
                "preco":       preco,
                "tempo":       tempo_norm,
                "disponivel":  disp_var.get(),
                "cor":         cor,
                "ingredientes": ings,
                "modo":        modo_p,
            }

            if modo_edicao:
                # Atualiza in-place preservando ordem
                nome_antigo = item["nome"]
                encontrado  = False
                for grupo in CARDAPIO:
                    for idx, it in enumerate(grupo["itens"]):
                        if it["nome"] == nome_antigo:
                            grupo["itens"][idx] = novo_item
                            encontrado = True
                            break
                    if encontrado:
                        # Mover para nova categoria se mudou
                        cat_atual_real = grupo["categoria"]
                        if cat_atual_real != cat:
                            grupo["itens"].pop(idx)
                            self._inserir_em_categoria(cat, novo_item)
                        break
            else:
                # Inserir na categoria escolhida (cria se não existir)
                self._inserir_em_categoria(cat, novo_item)

            db_cardapio_salvar(CARDAPIO)
            self._reload_cardapio()
            messagebox.showinfo(
                "Salvo",
                f"'{nome}' {'atualizado' if modo_edicao else 'adicionado'} com sucesso!")
            win.destroy()
            self.mostrar_cardapio()

        HoverButton(pad, "✔  Salvar Receita",
                    command=_salvar, font_size=12).pack(
                        fill="x", pady=(10, 0))

        HoverButton(win, "Cancelar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=18, pady=10)

    def _inserir_em_categoria(self, categoria: str, item: dict):
        """Insere item na categoria existente, ou cria nova categoria."""
        global CARDAPIO
        for grupo in CARDAPIO:
            if grupo["categoria"].lower() == categoria.lower():
                grupo["itens"].append(item)
                return
        # Nova categoria
        CARDAPIO.append({"categoria": categoria, "itens": [item]})

    # =========================================================================
    # FORMULÁRIO NOVA CATEGORIA — somente admin
    # =========================================================================
    def _abrir_form_nova_categoria(self):
        """Cria uma nova categoria vazia no cardápio."""
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
        tk.Label(head, text="Nova Categoria", bg=COLORS["dark"],
                 fg=COLORS["white"], font=(FONT, 13, "bold")).pack(
                     side="left", padx=20, pady=14)
        tk.Label(head, text="ADMIN", bg=COLORS["green"], fg=COLORS["white"],
                 font=(FONT, 8, "bold"), padx=8, pady=3).pack(
                     side="right", padx=18)

        pad = tk.Frame(win, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(pad, text="Nome da nova categoria", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w")
        e_cat = tk.Entry(pad, font=(FONT, 12), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"],
                         highlightthickness=1)
        e_cat.pack(fill="x", ipady=8, pady=(4, 14))
        e_cat.focus_set()

        def _criar():
            global CARDAPIO
            nome_cat = e_cat.get().strip()
            if not nome_cat:
                messagebox.showerror("Erro", "Informe o nome da categoria.",
                                     parent=win); return
            # Verifica duplicidade
            if any(g["categoria"].lower() == nome_cat.lower() for g in CARDAPIO):
                messagebox.showerror("Erro",
                                     "Ja existe uma categoria com este nome.",
                                     parent=win); return
            CARDAPIO.append({"categoria": nome_cat, "itens": []})
            db_cardapio_salvar(CARDAPIO)
            self._reload_cardapio()
            messagebox.showinfo("Criada",
                                f"Categoria '{nome_cat}' criada com sucesso!\n"
                                f"Adicione receitas a ela pelo botao '+ Nova Receita'.")
            win.destroy()
            self.mostrar_cardapio()

        e_cat.bind("<Return>", lambda e: _criar())
        HoverButton(pad, "✔  Criar Categoria",
                    command=_criar, font_size=11).pack(fill="x", pady=(0, 8))
        HoverButton(win, "Cancelar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=20, pady=(0, 12))

    # =========================================================================
    # FORMULÁRIO EDITAR CATEGORIA — somente admin
    # =========================================================================
    def _abrir_form_categoria(self, grupo: dict):
        """Permite renomear a categoria ou excluí-la (se vazia)."""
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
        tk.Label(head, text="Editar Categoria", bg=COLORS["dark"],
                 fg=COLORS["white"], font=(FONT, 13, "bold")).pack(
                     side="left", padx=20, pady=14)

        pad = tk.Frame(win, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(pad, text="Nome da categoria", bg=COLORS["bg"],
                 fg=COLORS["dark_soft"], font=(FONT, 9, "bold")).pack(anchor="w")
        e_cat = tk.Entry(pad, font=(FONT, 12), relief="flat",
                         bg=COLORS["card"], fg=COLORS["dark"],
                         insertbackground=COLORS["dark"],
                         highlightbackground=COLORS["gray_light"],
                         highlightthickness=1)
        e_cat.pack(fill="x", ipady=8, pady=(4, 12))
        e_cat.insert(0, grupo["categoria"])

        def _salvar_cat():
            global CARDAPIO
            novo_nome = e_cat.get().strip()
            if not novo_nome:
                messagebox.showerror("Erro", "Nome nao pode ser vazio.",
                                     parent=win); return
            grupo["categoria"] = novo_nome
            db_cardapio_salvar(CARDAPIO)
            self._reload_cardapio()
            win.destroy()
            self.mostrar_cardapio()

        def _excluir_cat():
            global CARDAPIO
            if grupo["itens"]:
                messagebox.showerror(
                    "Nao permitido",
                    "Remova todos os itens da categoria antes de excluí-la.",
                    parent=win); return
            if not messagebox.askyesno(
                    "Confirmar",
                    f"Excluir a categoria '{grupo['categoria']}'?",
                    parent=win): return
            CARDAPIO = [g for g in CARDAPIO if g is not grupo]
            db_cardapio_salvar(CARDAPIO)
            self._reload_cardapio()
            win.destroy()
            self.mostrar_cardapio()

        HoverButton(pad, "✔  Salvar nome",
                    command=_salvar_cat, font_size=11).pack(fill="x", pady=(0, 8))
        HoverButton(pad, "⚲  Excluir categoria (se vazia)",
                    command=_excluir_cat,
                    bg=COLORS["red_light"], fg=COLORS["red"],
                    hover_bg=COLORS["red"], font_size=10).pack(fill="x")
        HoverButton(win, "Cancelar", command=win.destroy,
                    bg=COLORS["dark"], hover_bg=COLORS["dark_soft"],
                    font_size=10).pack(fill="x", padx=20, pady=10)

    # =========================================================================
    # NOVO PEDIDO
    # =========================================================================
    def abrir_novo_pedido(self):
        win = tk.Toplevel(self)
        win.title("Novo Pedido")
        win.geometry("400x680")
        win.configure(bg=COLORS["bg"])
        win.transient(self); win.grab_set()
        carrinho = {}

        head = tk.Frame(win, bg=COLORS["dark"], height=64)
        head.pack(fill="x"); head.pack_propagate(False)
        tk.Label(head, text="Iniciar Atendimento", bg=COLORS["dark"],
                 fg=COLORS["white"], font=(FONT,14,"bold")).pack(anchor="w", padx=20, pady=18)

        body = tk.Frame(win, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=14)

        tk.Label(body, text="Selecione a mesa", bg=COLORS["bg"],
                 fg=COLORS["dark"], font=(FONT,11,"bold")).pack(anchor="w")
        mesa_var = tk.StringVar(value="Mesa 01")
        ttk.Combobox(body, textvariable=mesa_var,
                     values=[f"Mesa {i:02d}" for i in range(1,TOTAL_MESAS+1)],
                     state="readonly", font=(FONT,11)).pack(fill="x", pady=(6,14), ipady=4)

        tk.Label(body, text="Adicionar itens do cardapio", bg=COLORS["bg"],
                 fg=COLORS["dark"], font=(FONT,11,"bold")).pack(anchor="w")
        iw = tk.Frame(body, bg=COLORS["bg"])
        iw.pack(fill="x", pady=(6,12))

        total_var = tk.StringVar(value=brl(0))
        resumo_f  = tk.Frame(body, bg=COLORS["card"],
                             highlightbackground=COLORS["gray_light"], highlightthickness=1)

        def atualizar():
            total = sum(c["item"]["preco"]*c["qtd"] for c in carrinho.values())
            total_var.set(brl(total))
            for w in resumo_f.winfo_children(): w.destroy()
            ri = tk.Frame(resumo_f, bg=COLORS["card"])
            ri.pack(fill="x", padx=12, pady=10)
            tk.Label(ri, text="Resumo do pedido", bg=COLORS["card"],
                     fg=COLORS["dark"], font=(FONT,10,"bold")).pack(anchor="w")
            if not carrinho:
                tk.Label(ri, text="Nenhum item adicionado.",
                         bg=COLORS["card"], fg=COLORS["gray"],
                         font=(FONT,9)).pack(anchor="w", pady=4)
            for c in carrinho.values():
                r = tk.Frame(ri, bg=COLORS["card"]); r.pack(fill="x", pady=2)
                tk.Label(r, text=f"{c['qtd']}x {c['item']['nome']}",
                         bg=COLORS["card"], fg=COLORS["dark_soft"],
                         font=(FONT,9), wraplength=220, justify="left",
                         anchor="w").pack(side="left")
                tk.Label(r, text=brl(c['item']['preco']*c['qtd']),
                         bg=COLORS["card"], fg=COLORS["dark"],
                         font=(FONT,9,"bold")).pack(side="right")
            tk.Frame(ri, bg=COLORS["gray_light"], height=1).pack(fill="x", pady=6)
            tr = tk.Frame(ri, bg=COLORS["card"]); tr.pack(fill="x")
            tk.Label(tr, text="Total", bg=COLORS["card"], fg=COLORS["dark"],
                     font=(FONT,11,"bold")).pack(side="left")
            tk.Label(tr, textvariable=total_var, bg=COLORS["card"],
                     fg=COLORS["green"], font=(FONT,13,"bold")).pack(side="right")

        def add_item(item):
            if not item["disponivel"]:
                messagebox.showwarning("Indisponivel", f"{item['nome']} esta indisponivel.")
                return
            if item["nome"] in carrinho: carrinho[item["nome"]]["qtd"] += 1
            else: carrinho[item["nome"]] = {"item": item, "qtd": 1}
            atualizar()

        for grupo in CARDAPIO:
            for item in grupo["itens"]:
                r = tk.Frame(iw, bg=COLORS["card"],
                             highlightbackground=COLORS["gray_light"], highlightthickness=1)
                r.pack(fill="x", pady=3)
                ri = tk.Frame(r, bg=COLORS["card"]); ri.pack(fill="x", padx=10, pady=8)
                tk.Label(ri, text=item["nome"], bg=COLORS["card"], fg=COLORS["dark"],
                         font=(FONT,9,"bold"), wraplength=200,
                         justify="left", anchor="w").pack(side="left")
                tk.Label(ri, text=brl(item["preco"]), bg=COLORS["card"],
                         fg=COLORS["gray"], font=(FONT,9)).pack(side="left", padx=8)
                HoverButton(ri, "+", command=lambda it=item: add_item(it),
                            font_size=10, padx=10, pady=2).pack(side="right")

        resumo_f.pack(fill="x", pady=(0,12))
        atualizar()

        bots = tk.Frame(win, bg=COLORS["bg"])
        bots.pack(fill="x", padx=18, pady=12)

        def finalizar():
            if not carrinho:
                messagebox.showwarning("Pedido vazio", "Adicione ao menos um item.")
                return
            os_num  = f"OS-{self.os_counter}"
            self.os_counter += 1
            total   = sum(c["item"]["preco"]*c["qtd"] for c in carrinho.values())
            qtd     = sum(c["qtd"] for c in carrinho.values())
            mesa    = int(mesa_var.get().split()[-1])
            agora   = datetime.now().strftime("%H:%M")
            itens_l = [{"nome":c["item"]["nome"],"qtd":c["qtd"],"preco":c["item"]["preco"]}
                       for c in carrinho.values()]
            novo = {"os":os_num,"mesa":mesa,"status":"Aguardando",
                    "inicio":agora,"itens":qtd,"total":total,
                    "mesa_liberada":False,"itens_lista":itens_l}
            self.pedidos.insert(0, novo)
            db_pedido_salvar(novo)
            messagebox.showinfo("Pedido confirmado",
                                f"{os_num} gerada!\nMesa {mesa:02d}  —  {qtd} itens\n"
                                f"Total: {brl(total)}\nRegistrado: {agora}")
            win.destroy()
            self.navegar("pedidos")

        def cancelar():
            if messagebox.askyesno("Cancelar","Descartar este pedido?"):
                win.destroy()

        HoverButton(bots, "Finalizar Pedido", command=finalizar, font_size=11).pack(fill="x", pady=(0,8))
        HoverButton(bots, "Cancelar", command=cancelar,
                    bg=COLORS["red_light"], fg=COLORS["red"],
                    hover_bg=COLORS["red"], font_size=11).pack(fill="x")


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    app = SGCPApp()
    app.mainloop()

import os, sys

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
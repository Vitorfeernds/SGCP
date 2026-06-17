from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
USUARIOS_FILE = DATA_DIR / "usuarios.json"
PEDIDOS_FILE = DATA_DIR / "pedidos.json"
CARDAPIO_FILE = DATA_DIR / "cardapio.json"
ENV_FILE = DATA_DIR / ".env"
GITIGNORE_FILE = BASE_DIR / ".gitignore"

PERFIL_ADMIN     = "admin"
PERFIL_ATENDENTE = "atendente"

TOTAL_MESAS = 14   # mesas existentes no estabelecimento
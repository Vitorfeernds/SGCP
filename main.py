import os
 
from app.config import DATA_DIR, GITIGNORE_FILE
from app.cardapio_padrao import CARDAPIO_PADRAO
from app.theme import load_theme
 
from app.db import connection
from app.db import usuarios
from app.db import pedidos
from app.db import cardapio
import app.state as state
from app.logic.cardapio import reconstruir_indice
 
from app.views.base      import BaseApp
from app.views.login     import LoginMixin
from app.views.dashboard import DashboardMixin
from app.views.pedidos   import PedidosMixin
from app.views.cardapio  import CardapioMixin
from app.views.usuarios  import UsuariosMixin
 
 
# ── Bootstrap de arquivos/pastas ──────────────────────────────────────────────
 
def _bootstrap_arquivos() -> None:
    """Garante que data/ e .gitignore existam antes de qualquer leitura."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(GITIGNORE_FILE):
        with open(GITIGNORE_FILE, "w", encoding="utf-8") as f:
            f.write("# === SGCP — não versionar ===\n")
            f.write("data/\n*.json\n*.env\n__pycache__/\n")
 
 
# ── Classe final por composição de mixins ─────────────────────────────────────
 
class SGCPApp(
    LoginMixin,
    DashboardMixin,
    PedidosMixin,
    CardapioMixin,
    UsuariosMixin,
    BaseApp,
):
    """
    Aplicação completa.
 
    A ordem dos mixins define a MRO (Method Resolution Order) — não é
    relevante aqui pois não há sobreposição de nomes de método entre eles,
    mas BaseApp deve permanecer por último (é quem herda de tk.Tk).
    """
 
    def __init__(self):
        super().__init__()
 
        # 1) Persistência: tenta MongoDB, cai para JSON local
        conexao.inicializar()
        usuarios_db.seed(conexao.MONGO_OK)
        pedidos_db.seed(conexao.MONGO_OK)
        cardapio_db.seed(conexao.MONGO_OK, CARDAPIO_PADRAO)
 
        # 2) Tema salvo
        load_theme()
        self.configure(bg=self.cget("bg"))  # refresca cor de fundo após tema
 
        # 3) Estado em memória
        state.CARDAPIO = cardapio_db.carregar(CARDAPIO_PADRAO)
        reconstruir_indice()
 
        self.pedidos     = pedidos_db.carregar()
        self.os_counter  = self._proximo_os()
 
        # 4) Tela inicial
        self.mostrar_login()
        self._tick()
 
 
# ── Entry point ────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    _bootstrap_arquivos()
    app = SGCPApp()
    app.mainloop()
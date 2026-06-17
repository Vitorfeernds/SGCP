import json, os
from app.config import ENV_FILE, USUARIOS_FILE, PEDIDOS_FILE, CARDAPIO_FILE
from pymongo import MongoClient
import hashlib

def _hash_senha(senha: str) -> str:
    return hashlib.sha256(
        senha.encode("utf-8")
    ).hexdigest()

# ============================================================================
# MONGODB — camada de abstração com fallback para JSON local
# ============================================================================
_mongo_client = None
_mongo_db     = None
MONGO_OK     = False   # True somente quando conexão real estiver ativa

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
    global _mongo_client, _mongo_db, MONGO_OK
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
        MONGO_OK = True
        print(f"[DB] MongoDB conectado: {db_name}")
        _seed_mongo()
    except Exception as e:
        MONGO_OK = False
        print(f"[DB] MongoDB indisponivel ({e}). Usando JSON local.")


def _seed_mongo():
    #Semeia dados iniciais no MongoDB se as coleções estiverem vazias.
    #Também importa dados do JSON local para o MongoDB na primeira vez.
    if not MONGO_OK:
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
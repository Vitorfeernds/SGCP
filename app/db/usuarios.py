import hashlib
import json
import os
from app.config import USUARIOS_FILE, PERFIL_ADMIN, PERFIL_ATENDENTE
from app.db.connection import MONGO_OK, _json_load, _json_save, _mongo_db


def seed(mongo_ok):    #Garante que exista pelo menos um usuário admin. Se o MongoDB estiver disponível, semeia diretamente nele; caso contrário, semeia no JSON local.
    if mongo_ok:
        if _mongo_db["usuarios"].count_documents({}) == 0:
            _mongo_db["usuarios"].insert_one({
                "email": "admin@guanambusiness.com",
                "hash_senha": _hash_senha("admin123"),
                "nome": "Administrador",
                "perfil": PERFIL_ADMIN
            })

def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def carregar_usuarios() -> dict:
    if MONGO_OK:
        docs = list(_mongo_db["usuarios"].find({}, {"_id": 0}))
        return {d["email"]: d for d in docs}
    return _json_load(USUARIOS_FILE, {})


def salvar_usuarios(usuarios: dict) -> None:
    if MONGO_OK:
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
    if MONGO_OK:
        res = _mongo_db["usuarios"].delete_one({"email": email_alvo})
        return (True, "Conta removida.") if res.deleted_count else (False, "Usuario nao encontrado.")
    usuarios = carregar_usuarios()
    if email_alvo not in usuarios:
        return False, "Usuario nao encontrado."
    del usuarios[email_alvo]
    salvar_usuarios(usuarios)
    return True, "Conta removida com sucesso."



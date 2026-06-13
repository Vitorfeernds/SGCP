
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

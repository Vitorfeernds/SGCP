def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()

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
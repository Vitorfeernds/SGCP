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
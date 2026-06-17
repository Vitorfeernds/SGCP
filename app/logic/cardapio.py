import app.state as state

def reconstruir_indice():
    state.CARDAPIO_IDX = _indice_cardapio()
    return state.CARDAPIO_IDX

def _indice_cardapio() -> dict:
    idx = {}

    for grupo in state.CARDAPIO:
        for item in grupo["itens"]:
            idx[item["nome"]] = item

    return idx

def _tempo_para_minutos(s: str) -> int:
    try:
        return int(s.split()[0])
    except Exception:
        return 0

def calcular_tempo_medio(itens_pedido: list) -> str:
    if not state.CARDAPIO_IDX:
        reconstruir_indice()

    tempos = [
        _tempo_para_minutos(d["tempo"])
        for e in itens_pedido
        if (d := state.CARDAPIO_IDX.get(e["nome"])) and d.get("tempo")
    ]

    if not tempos:
        return ""

    return f"~{round(sum(tempos) / len(tempos))} min"

def categoria_do_item(nome_item: str) -> str:
    """
    Retorna a categoria de um item do cardápio.
    """
    for grupo in state.CARDAPIO:
        for item in grupo["itens"]:
            if item["nome"] == nome_item:
                return grupo["categoria"]

    return ""


def inserir_em_categoria(categoria: str, item: dict) -> None:
    """
    Insere um item em uma categoria existente.
    Caso a categoria não exista, cria automaticamente.
    """
    for grupo in state.CARDAPIO:
        if grupo["categoria"].lower() == categoria.lower():
            grupo["itens"].append(item)
            return

    state.CARDAPIO.append({
        "categoria": categoria,
        "itens": [item]
    })

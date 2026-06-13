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
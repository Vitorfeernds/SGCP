# ============================================================================
# HELPERS — MESAS OCUPADAS
# ============================================================================
def mesas_ocupadas(pedidos: list) -> set:
    #Retorna o conjunto de números de mesa que estão ocupadas (pedido ativo E mesa_liberada=False).
    ocupadas = set()
    for p in pedidos:
        if p.get("status") in ("Aguardando", "Em preparo") and not p.get("mesa_liberada", False):
            ocupadas.add(p["mesa"])
    return ocupadas


# ============================================================================
# HELPERS — GRÁFICOS DINÂMICOS
# ============================================================================
def _calcular_fluxo(pedidos: list):
    #Agrupa pedidos por hora de início → retorna (labels, valores)
    #com as 6 horas mais recentes que tenham pelo menos 1 pedido,
    #mais eventuais horas intermediárias sem pedido para manter continuidade.
    contagem: dict[int, int] = defaultdict(int)
    for p in pedidos:
        try:
            hora = int(p["inicio"].split(":")[0])
            contagem[hora] += 1
        except Exception:
            pass

    if not contagem:
        h = datetime.now().hour
        return ([f"{(h-i)%24:02d}h" for i in range(5, -1, -1)], [0]*6)

    horas_com = sorted(contagem.keys())
    h_min, h_max = horas_com[0], horas_com[-1]
    # preenche horas sem pedido no intervalo
    todas = list(range(h_min, h_max + 1))
    # limita a 6 horas (as últimas)
    if len(todas) > 6:
        todas = todas[-6:]
    labels  = [f"{h:02d}h" for h in todas]
    valores = [contagem.get(h, 0) for h in todas]
    return labels, valores


def _calcular_vendas(pedidos: list):
    #Agrupa faturamento por hora → retorna valores por hora
    #no mesmo intervalo que _calcular_fluxo.
    fat: dict[int, float] = defaultdict(float)
    for p in pedidos:
        try:
            hora = int(p["inicio"].split(":")[0])
            fat[hora] += p.get("total", 0)
        except Exception:
            pass

    if not fat:
        return [0] * 6

    # usa exatamente as mesmas horas que _calcular_fluxo
    labels, _ = _calcular_fluxo(pedidos)
    return [round(fat.get(int(l.replace("h", "")), 0)) for l in labels]
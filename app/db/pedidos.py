import json, os
from app.config import DATA_DIR, PEDIDOS_FILE, PEDIDOS_FILE
from app.db.connection import _mongo_db, _MONGO_OK
from app import PEDIDOS_FILE


def db_pedidos_carregar() -> list:
    if _MONGO_OK:
        docs = list(_mongo_db["pedidos"].find({}, {"_id": 0}))
        docs.sort(key=lambda d: d.get("os", ""), reverse=True)
        return docs
    return json.load(PEDIDOS_FILE, [])


def db_pedido_salvar(pedido: dict) -> None:
    #Insere ou atualiza um pedido (upsert por 'os').
    if _MONGO_OK:
        _mongo_db["pedidos"].update_one(
            {"os": pedido["os"]}, {"$set": pedido}, upsert=True)
    else:
        pedidos = json.load(PEDIDOS_FILE, [])
        idx = next((i for i, p in enumerate(pedidos) if p["os"] == pedido["os"]), -1)
        if idx >= 0:
            pedidos[idx] = pedido
        else:
            pedidos.insert(0, pedido)
        json.save(PEDIDOS_FILE, pedidos)


def db_pedido_atualizar_campo(os_num: str, campo: str, valor) -> None:
    #Atualiza um único campo de um pedido já existente.
    if _MONGO_OK:
        _mongo_db["pedidos"].update_one({"os": os_num}, {"$set": {campo: valor}})
    else:
        pedidos = json.load(PEDIDOS_FILE, [])
        for p in pedidos:
            if p["os"] == os_num:
                p[campo] = valor
                break
        json.save(PEDIDOS_FILE, pedidos)
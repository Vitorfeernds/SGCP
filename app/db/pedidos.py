from app.config import PEDIDOS_FILE
from app.db.connection import _json_load, _json_save
import app.db.connection as connection


def db_pedidos_carregar() -> list:
    if connection.MONGO_OK:
        docs = list(connection._mongo_db["pedidos"].find({}, {"_id": 0}))
        docs.sort(key=lambda d: d.get("os", ""), reverse=True)
        return docs
    return _json_load(PEDIDOS_FILE, [])


def db_pedido_salvar(pedido: dict) -> None:
    #Insere ou atualiza um pedido (upsert por 'os').
    if connection.MONGO_OK:
        connection._mongo_db["pedidos"].update_one(
            {"os": pedido["os"]}, {"$set": pedido}, upsert=True)
    else:
        pedidos = _json_load(PEDIDOS_FILE, [])
        idx = next((i for i, p in enumerate(pedidos) if p["os"] == pedido["os"]), -1)
        if idx >= 0:
            pedidos[idx] = pedido
        else:
            pedidos.insert(0, pedido)
        _json_save(PEDIDOS_FILE, pedidos)


def db_pedido_atualizar_campo(os_num: str, campo: str, valor) -> None:
    #Atualiza um único campo de um pedido já existente.
    if connection.MONGO_OK:
        connection._mongo_db["pedidos"].update_one({"os": os_num}, {"$set": {campo: valor}})
    else:
        pedidos = _json_load(PEDIDOS_FILE, [])
        for p in pedidos:
            if p["os"] == os_num:
                p[campo] = valor
                break
        _json_save(PEDIDOS_FILE, pedidos)



seed = lambda mongo_ok: None  #Não há necessidade de semear pedidos, pois eles são criados dinamicamente pela aplicação.
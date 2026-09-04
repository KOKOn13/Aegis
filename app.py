from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from database.sqlite_db import (
    init_db,
    # Artículos
    get_articulos, buscar_articulos, create_articulo, update_articulo,
    # Campañas
    get_campanas, get_campana, create_campana, update_campana, toggle_campana,
    add_centro_to_campana, remove_centro_from_campana,
    # Centros
    get_centros, get_centro, create_centro, update_centro, toggle_centro,
    # Usuarios
    get_usuarios, get_usuario, create_usuario, update_usuario, toggle_usuario, validate_login,
    # Inventario
    get_inventario, get_stock,
    # Movimientos
    get_movimientos,
    registrar_recepcion, registrar_entrega, registrar_merma,
    registrar_transferencia, registrar_ajuste, confirmar_movimiento,
    # Instituciones
    get_instituciones,
    # Validations
    VALID_MOTIVOS,
)

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
init_db()


def ok(data, code: int = 200):
    return jsonify(data), code


def err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/login")
def api_login():
    data = request.get_json(force=True) or {}
    u = validate_login(data.get("username", "").strip(), data.get("password", "").strip())
    if not u:
        return err("Usuario o contraseña incorrectos.", 401)
    return ok({k: v for k, v in u.items() if k != "password"})


# ── Artículos ─────────────────────────────────────────────────────────────────

@app.get("/api/articulos")
def api_get_articulos():
    return ok(get_articulos())


@app.get("/api/articulos/buscar")
def api_buscar_articulos():
    q = request.args.get("q", "").strip()
    return ok(buscar_articulos(q) if q else get_articulos(activo_only=True))


_VALID_CAT = {"no_perecedero", "perecedero", "ropa", "limpieza", "medicamento", "otro"}
_VALID_UNI = {"pieza", "kg", "l", "bolsa", "caja"}


@app.patch("/api/articulos/<articulo_id>")
def api_update_articulo(articulo_id: str):
    data = request.get_json(force=True) or {}
    if "categoria" in data and data["categoria"] not in _VALID_CAT:
        return err("Categoría inválida.")
    if "unidad" in data and data["unidad"] not in _VALID_UNI:
        return err("Unidad inválida.")
    result = update_articulo(articulo_id, data)
    return ok(result) if result else err("Artículo no encontrado.", 404)


@app.post("/api/articulos")
def api_crear_articulo():
    data = request.get_json(force=True) or {}
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return err("El nombre es obligatorio.")
    categoria = data.get("categoria", "")
    unidad = data.get("unidad", "")
    if categoria not in _VALID_CAT:
        return err(f"Categoría inválida. Opciones: {', '.join(sorted(_VALID_CAT))}")
    if unidad not in _VALID_UNI:
        return err(f"Unidad inválida. Opciones: {', '.join(sorted(_VALID_UNI))}")
    try:
        return ok(create_articulo(nombre, categoria, unidad), 201)
    except Exception as e:
        return err(str(e))


# ── Campañas ──────────────────────────────────────────────────────────────────

@app.get("/api/campanas")
def api_get_campanas():
    return ok(get_campanas())


@app.post("/api/campanas")
def api_crear_campana():
    data = request.get_json(force=True) or {}
    try:
        return ok(create_campana(
            nombre=data.get("nombre", ""),
            fecha_inicio=data.get("fecha_inicio", ""),
            fecha_fin=data.get("fecha_fin", ""),
            descripcion=data.get("descripcion", ""),
        ), 201)
    except Exception as e:
        return err(str(e))


@app.patch("/api/campanas/<campana_id>")
def api_update_campana(campana_id: str):
    data = request.get_json(force=True) or {}
    result = update_campana(campana_id, data)
    return ok(result) if result else err("Campaña no encontrada.", 404)


@app.patch("/api/campanas/<campana_id>/activar")
def api_activar_campana(campana_id: str):
    result = toggle_campana(campana_id, True)
    return ok(result) if result else err("Campaña no encontrada.", 404)


@app.patch("/api/campanas/<campana_id>/desactivar")
def api_desactivar_campana(campana_id: str):
    result = toggle_campana(campana_id, False)
    return ok(result) if result else err("Campaña no encontrada.", 404)


@app.post("/api/campanas/<campana_id>/centros")
def api_agregar_centro_campana(campana_id: str):
    data = request.get_json(force=True) or {}
    centro_id = data.get("centro_id", "")
    if not centro_id:
        return err("centro_id requerido.")
    result = add_centro_to_campana(centro_id, campana_id)
    return ok(result) if result else err("Centro no encontrado.", 404)


@app.delete("/api/campanas/<campana_id>/centros/<centro_id>")
def api_quitar_centro_campana(campana_id: str, centro_id: str):
    result = remove_centro_from_campana(centro_id, campana_id)
    return ok(result) if result else err("Centro no encontrado.", 404)


# ── Centros ───────────────────────────────────────────────────────────────────

@app.get("/api/centros")
def api_get_centros():
    return ok(get_centros())


@app.post("/api/centros")
def api_crear_centro():
    data = request.get_json(force=True) or {}
    nombre = data.get("nombre", "").strip()
    institucion = data.get("institucion", "").strip()
    ubicacion = data.get("ubicacion", "").strip()
    if not nombre or not institucion or not ubicacion:
        return err("Nombre, institución y ubicación son obligatorios.")
    try:
        return ok(create_centro(nombre, institucion, ubicacion,
                                encargado_id=data.get("encargado_id"),
                                campanas=data.get("campanas"),
                                activo=data.get("activo", True),
                                lat=data.get("lat"),
                                lng=data.get("lng"),
                                cp=data.get("cp"),
                                calle=data.get("calle"),
                                colonia=data.get("colonia"),
                                ciudad=data.get("ciudad"),
                                estado=data.get("estado")), 201)
    except Exception as e:
        return err(str(e))


@app.patch("/api/centros/<centro_id>")
def api_update_centro(centro_id: str):
    data = request.get_json(force=True) or {}
    result = update_centro(centro_id, data)
    return ok(result) if result else err("Centro no encontrado.", 404)


@app.patch("/api/centros/<centro_id>/activar")
def api_activar_centro(centro_id: str):
    result = toggle_centro(centro_id, True)
    return ok(result) if result else err("Centro no encontrado.", 404)


@app.patch("/api/centros/<centro_id>/desactivar")
def api_desactivar_centro(centro_id: str):
    result = toggle_centro(centro_id, False)
    return ok(result) if result else err("Centro no encontrado.", 404)


# ── Movimientos ───────────────────────────────────────────────────────────────

@app.get("/api/movimientos")
def api_get_movimientos():
    return ok(get_movimientos(
        centro_id=request.args.get("centro_id"),
        campana_id=request.args.get("campana_id"),
    ))


@app.patch("/api/movimientos/<mov_id>/confirmar")
def api_confirmar(mov_id: str):
    result = confirmar_movimiento(mov_id)
    return ok(result) if result else err("Movimiento no encontrado.", 404)


@app.delete("/api/movimientos/<mov_id>")
def api_delete_movimiento(mov_id: str):
    from database.sqlite_db import _conn
    with _conn() as conn:
        m = conn.execute("SELECT tipo FROM movimientos WHERE id=?", (mov_id,)).fetchone()
        if not m:
            return err("Movimiento no encontrado.", 404)
        if m["tipo"] != "merma":
            return err("Solo se pueden eliminar mermas rechazadas.", 400)
        conn.execute("DELETE FROM movimientos WHERE id=?", (mov_id,))
        conn.commit()
    return ok({"deleted": mov_id})


@app.post("/api/movimientos/recepcion")
def api_recepcion():
    data = request.get_json(force=True) or {}
    try:
        return ok(registrar_recepcion(
            centro_id=data["centro_id"],
            campana_id=data["campana_id"],
            articulo_id=data["articulo_id"],
            cantidad=float(data["cantidad"]),
            actor_id=data["actor_id"],
            donante=data.get("donante"),
            observaciones=data.get("observaciones", ""),
        ), 201)
    except KeyError as e:
        return err(f"Campo requerido: {e}")
    except ValueError as e:
        return err(str(e))


@app.post("/api/movimientos/entrega")
def api_entrega():
    data = request.get_json(force=True) or {}
    try:
        return ok(registrar_entrega(
            centro_id=data["centro_id"],
            campana_id=data["campana_id"],
            articulo_id=data["articulo_id"],
            cantidad=float(data["cantidad"]),
            actor_id=data["actor_id"],
            destino_id=data.get("destino_id"),
            institucion_receptora_id=data.get("institucion_receptora_id"),
            observaciones=data.get("observaciones", ""),
        ), 201)
    except KeyError as e:
        return err(f"Campo requerido: {e}")
    except ValueError as e:
        return err(str(e))


@app.post("/api/movimientos/merma")
def api_merma():
    data = request.get_json(force=True) or {}
    motivo = data.get("motivo", "").strip()
    if motivo not in VALID_MOTIVOS:
        return err(f"Motivo obligatorio para merma. Opciones: {', '.join(sorted(VALID_MOTIVOS))}")
    try:
        return ok(registrar_merma(
            centro_id=data["centro_id"],
            campana_id=data["campana_id"],
            articulo_id=data["articulo_id"],
            cantidad=float(data["cantidad"]),
            actor_id=data["actor_id"],
            motivo=motivo,
            observaciones=data.get("observaciones", ""),
        ), 201)
    except KeyError as e:
        return err(f"Campo requerido: {e}")
    except ValueError as e:
        return err(str(e))


@app.post("/api/movimientos/transferencia")
def api_transferencia():
    data = request.get_json(force=True) or {}
    try:
        return ok(registrar_transferencia(
            origen_id=data["origen_id"],
            destino_id=data["destino_id"],
            campana_id=data["campana_id"],
            articulo_id=data["articulo_id"],
            cantidad=float(data["cantidad"]),
            actor_id=data["actor_id"],
            observaciones=data.get("observaciones", ""),
        ), 201)
    except KeyError as e:
        return err(f"Campo requerido: {e}")
    except ValueError as e:
        return err(str(e))


@app.post("/api/movimientos/ajuste")
def api_ajuste():
    data = request.get_json(force=True) or {}
    motivo = data.get("motivo", "").strip()
    if motivo not in VALID_MOTIVOS:
        return err(f"Motivo obligatorio para ajuste. Opciones: {', '.join(sorted(VALID_MOTIVOS))}")
    try:
        return ok(registrar_ajuste(
            centro_id=data["centro_id"],
            campana_id=data["campana_id"],
            articulo_id=data["articulo_id"],
            cantidad=float(data["cantidad"]),
            actor_id=data["actor_id"],
            tipo=data.get("tipo", "positivo"),
            motivo=motivo,
            observaciones=data.get("observaciones", ""),
        ), 201)
    except KeyError as e:
        return err(f"Campo requerido: {e}")
    except ValueError as e:
        return err(str(e))


# ── Usuarios ──────────────────────────────────────────────────────────────────

@app.get("/api/usuarios")
def api_get_usuarios():
    return ok([{k: v for k, v in u.items() if k != "password"} for u in get_usuarios()])


@app.post("/api/usuarios")
def api_crear_usuario():
    data = request.get_json(force=True) or {}
    nombre   = data.get("nombre","").strip()
    username = data.get("username","").strip()
    password = data.get("password","").strip()
    rol      = data.get("rol","").strip()
    if not nombre or not username or not password or not rol:
        return err("Nombre, usuario, contraseña y rol son obligatorios.")
    try:
        u = create_usuario(nombre, username, password, rol,
                           centro_id=data.get("centro_id") or None,
                           campana_id=data.get("campana_id") or None,
                           institucion_id=data.get("institucion_id") or None)
        return ok({k: v for k, v in u.items() if k != "password"}, 201)
    except ValueError as e:
        return err(str(e))


@app.patch("/api/usuarios/<usuario_id>")
def api_update_usuario(usuario_id: str):
    data = request.get_json(force=True) or {}
    try:
        u = update_usuario(usuario_id, data)
        return ok({k: v for k, v in u.items() if k != "password"}) if u else err("Usuario no encontrado.", 404)
    except ValueError as e:
        return err(str(e))


@app.patch("/api/usuarios/<usuario_id>/activar")
def api_activar_usuario(usuario_id: str):
    u = toggle_usuario(usuario_id, True)
    return ok({k: v for k, v in u.items() if k != "password"}) if u else err("Usuario no encontrado.", 404)


@app.patch("/api/usuarios/<usuario_id>/desactivar")
def api_desactivar_usuario(usuario_id: str):
    u = toggle_usuario(usuario_id, False)
    return ok({k: v for k, v in u.items() if k != "password"}) if u else err("Usuario no encontrado.", 404)


# ── Inventario ────────────────────────────────────────────────────────────────

@app.get("/api/inventario/<centro_id>/<campana_id>")
def api_inventario(centro_id: str, campana_id: str):
    return ok(get_inventario(centro_id, campana_id))


# ── Instituciones ─────────────────────────────────────────────────────────────

@app.get("/api/instituciones")
def api_get_instituciones():
    return ok(get_instituciones())


# ── Static ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return app.send_static_file("login.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)

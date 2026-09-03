"""
SQLite persistence layer for Acopio.
Migrates existing JSON data on first run. Single source of truth for all roles.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "acopio.db"
DATA_DIR = ROOT / "data"

# ── Connection ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _as_dict(row) -> Optional[Dict]:
    if row is None:
        return None
    d = dict(row)
    for k in ("activo", "activa", "confirmado"):
        if k in d:
            d[k] = bool(d[k])
    return d


def _as_list(rows) -> List[Dict]:
    return [_as_dict(r) for r in rows]


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS articulos (
    id       TEXT PRIMARY KEY,
    nombre   TEXT NOT NULL COLLATE NOCASE,
    categoria TEXT NOT NULL,
    unidad   TEXT NOT NULL,
    activo   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS instituciones (
    id       TEXT PRIMARY KEY,
    nombre   TEXT NOT NULL,
    tipo     TEXT,
    contacto TEXT,
    telefono TEXT,
    email    TEXT,
    activa   INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS campanas (
    id           TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin    TEXT NOT NULL,
    descripcion  TEXT DEFAULT '',
    activa       INTEGER NOT NULL DEFAULT 1,
    meta         REAL    NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS usuarios (
    id            TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    username      TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password      TEXT NOT NULL,
    rol           TEXT NOT NULL,
    centro_id     TEXT,
    campana_id    TEXT,
    institucion_id TEXT,
    activo        INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS centros (
    id           TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    institucion  TEXT NOT NULL,
    ubicacion    TEXT NOT NULL,
    encargado_id TEXT,
    activo       INTEGER NOT NULL DEFAULT 1,
    lat          REAL DEFAULT NULL,
    lng          REAL DEFAULT NULL,
    cp           TEXT DEFAULT NULL,
    calle        TEXT DEFAULT NULL,
    colonia      TEXT DEFAULT NULL,
    ciudad       TEXT DEFAULT NULL,
    estado       TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS centro_campanas (
    centro_id  TEXT NOT NULL REFERENCES centros(id),
    campana_id TEXT NOT NULL REFERENCES campanas(id),
    PRIMARY KEY (centro_id, campana_id)
);
CREATE TABLE IF NOT EXISTS movimientos (
    id                    TEXT PRIMARY KEY,
    tipo                  TEXT NOT NULL,
    centro_id             TEXT NOT NULL,
    campana_id            TEXT NOT NULL,
    articulo_id           TEXT NOT NULL,
    cantidad              REAL NOT NULL,
    fecha                 TEXT NOT NULL,
    actor_id              TEXT NOT NULL,
    destino_id            TEXT,
    motivo                TEXT,
    observaciones         TEXT DEFAULT '',
    donante               TEXT,
    institucion_receptora_id TEXT,
    transferencia_id      TEXT,
    ajuste_tipo           TEXT,
    confirmado            INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_mov_centro    ON movimientos(centro_id);
CREATE INDEX IF NOT EXISTS idx_mov_campana   ON movimientos(campana_id);
CREATE INDEX IF NOT EXISTS idx_mov_articulo  ON movimientos(articulo_id);
CREATE INDEX IF NOT EXISTS idx_art_nombre    ON articulos(nombre);
"""


# ── Init & Migration ──────────────────────────────────────────────────────────

def _load_json(name: str) -> Any:
    p = DATA_DIR / name
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript(_SCHEMA)
        # Migrations for columns added after initial deploy
        for stmt in [
            "ALTER TABLE campanas ADD COLUMN meta REAL NOT NULL DEFAULT 0",
            "ALTER TABLE centros ADD COLUMN lat REAL DEFAULT NULL",
            "ALTER TABLE centros ADD COLUMN lng REAL DEFAULT NULL",
            "ALTER TABLE centros ADD COLUMN cp TEXT DEFAULT NULL",
            "ALTER TABLE centros ADD COLUMN calle TEXT DEFAULT NULL",
            "ALTER TABLE centros ADD COLUMN colonia TEXT DEFAULT NULL",
            "ALTER TABLE centros ADD COLUMN ciudad TEXT DEFAULT NULL",
            "ALTER TABLE centros ADD COLUMN estado TEXT DEFAULT NULL",
        ]:
            try:
                conn.execute(stmt)
                conn.commit()
            except Exception:
                pass
        if conn.execute("SELECT COUNT(*) FROM articulos").fetchone()[0] == 0:
            _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    for a in _load_json("articulos.json"):
        conn.execute("INSERT OR IGNORE INTO articulos VALUES(?,?,?,?,?)",
                     (a["id"], a["nombre"], a["categoria"], a["unidad"], int(a.get("activo", True))))

    for i in _load_json("instituciones.json"):
        conn.execute("INSERT OR IGNORE INTO instituciones VALUES(?,?,?,?,?,?,?)",
                     (i["id"], i["nombre"], i.get("tipo"), i.get("contacto"),
                      i.get("telefono"), i.get("email"), int(i.get("activa", True))))

    for c in _load_json("campanas.json"):
        conn.execute("INSERT OR IGNORE INTO campanas VALUES(?,?,?,?,?,?)",
                     (c["id"], c["nombre"], c["fecha_inicio"], c["fecha_fin"],
                      c.get("descripcion", ""), int(c.get("activa", True))))

    for u in _load_json("usuarios.json"):
        conn.execute("INSERT OR IGNORE INTO usuarios VALUES(?,?,?,?,?,?,?,?,?)",
                     (u["id"], u["nombre"], u["username"], u["password"], u["rol"],
                      u.get("centro_id"), u.get("campana_id"), u.get("institucion_id"),
                      int(u.get("activo", True))))

    for c in _load_json("centros.json"):
        conn.execute("INSERT OR IGNORE INTO centros VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (c["id"], c["nombre"], c["institucion"], c["ubicacion"],
                      c.get("encargado_id"), int(c.get("activo", True)),
                      c.get("lat"), c.get("lng"),
                      c.get("cp"), c.get("calle"), c.get("colonia"),
                      c.get("ciudad"), c.get("estado")))
        for cam in c.get("campanas", []):
            conn.execute("INSERT OR IGNORE INTO centro_campanas VALUES(?,?)", (c["id"], cam))

    for m in _load_json("movimientos.json"):
        donante = json.dumps(m["donante"]) if m.get("donante") else None
        conn.execute(
            "INSERT OR IGNORE INTO movimientos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (m["id"], m["tipo"], m["centro_id"], m["campana_id"], m["articulo_id"],
             float(m["cantidad"]), m["fecha"], m["actor_id"], m.get("destino_id"),
             m.get("motivo"), m.get("observaciones", ""), donante,
             m.get("institucion_receptora_id"), m.get("transferencia_id"),
             m.get("ajuste_tipo"), int(m.get("confirmado", False))))

    conn.commit()


# ── ID helpers ────────────────────────────────────────────────────────────────

def _next_id(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    rows = conn.execute(f"SELECT id FROM {table} WHERE id LIKE ?", (f"{prefix}%",)).fetchall()
    nums = [int(r[0][len(prefix):]) for r in rows if r[0][len(prefix):].isdigit()]
    return f"{prefix}{max(nums, default=0) + 1:03d}"


# ── Stock helpers (internal, share connection) ────────────────────────────────

def _stock(conn: sqlite3.Connection, centro_id: str, campana_id: str, articulo_id: str) -> float:
    row = conn.execute("""
        SELECT COALESCE(SUM(
            CASE
                WHEN tipo = 'recepcion'             THEN  cantidad
                WHEN tipo = 'transferencia_entrada' THEN  cantidad
                WHEN tipo = 'ajuste' AND ajuste_tipo = 'positivo' THEN  cantidad
                WHEN tipo = 'ajuste' AND ajuste_tipo = 'negativo' THEN -cantidad
                WHEN tipo = 'ajuste'                THEN  cantidad
                WHEN tipo = 'merma' AND confirmado = 1 THEN -cantidad
                WHEN tipo = 'merma'                 THEN  0
                ELSE -cantidad
            END
        ), 0)
        FROM movimientos
        WHERE centro_id=? AND campana_id=? AND articulo_id=?
    """, (centro_id, campana_id, articulo_id)).fetchone()
    return float(row[0]) if row else 0.0


def _mov_dict(conn: sqlite3.Connection, mov_id: str) -> Dict:
    row = _as_dict(conn.execute("SELECT * FROM movimientos WHERE id=?", (mov_id,)).fetchone())
    if row and row.get("donante") and isinstance(row["donante"], str):
        try:
            row["donante"] = json.loads(row["donante"])
        except Exception:
            pass
    return row


def _insert_mov(conn: sqlite3.Connection, tipo: str, centro_id: str, campana_id: str,
                articulo_id: str, cantidad: float, actor_id: str, **kw) -> Dict:
    mov_id = _next_id(conn, "movimientos", "M")
    fecha = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    donante = kw.get("donante")
    conn.execute(
        "INSERT INTO movimientos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (mov_id, tipo, centro_id, campana_id, articulo_id, float(cantidad),
         fecha, actor_id, kw.get("destino_id"), kw.get("motivo"),
         kw.get("observaciones", ""),
         json.dumps(donante) if donante else None,
         kw.get("institucion_receptora_id"), kw.get("transferencia_id"),
         kw.get("ajuste_tipo"), 0))
    return _mov_dict(conn, mov_id)


# ── Artículos ─────────────────────────────────────────────────────────────────

def get_articulos(activo_only: bool = False) -> List[Dict]:
    with _conn() as conn:
        q = "SELECT * FROM articulos" + (" WHERE activo=1" if activo_only else "") + " ORDER BY nombre"
        return _as_list(conn.execute(q).fetchall())


def buscar_articulos(q: str) -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM articulos WHERE nombre LIKE ? AND activo=1 ORDER BY nombre LIMIT 12",
            (f"%{q}%",)).fetchall()
        return _as_list(rows)


def update_articulo(articulo_id: str, data: Dict) -> Optional[Dict]:
    allowed = {"nombre", "categoria", "unidad"}
    fields = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if k in allowed and v is not None}
    if not fields:
        with _conn() as conn:
            return _as_dict(conn.execute("SELECT * FROM articulos WHERE id=?", (articulo_id,)).fetchone())
    with _conn() as conn:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE articulos SET {sets} WHERE id=?", [*fields.values(), articulo_id])
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM articulos WHERE id=?", (articulo_id,)).fetchone())


def create_articulo(nombre: str, categoria: str, unidad: str) -> Dict:
    with _conn() as conn:
        art_id = _next_id(conn, "articulos", "A")
        conn.execute("INSERT INTO articulos VALUES(?,?,?,?,1)", (art_id, nombre.strip(), categoria, unidad))
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM articulos WHERE id=?", (art_id,)).fetchone())


# ── Campañas ──────────────────────────────────────────────────────────────────

def get_campanas() -> List[Dict]:
    with _conn() as conn:
        return _as_list(conn.execute("SELECT * FROM campanas ORDER BY fecha_inicio").fetchall())


def get_campana(campana_id: str) -> Optional[Dict]:
    with _conn() as conn:
        return _as_dict(conn.execute("SELECT * FROM campanas WHERE id=?", (campana_id,)).fetchone())


def create_campana(nombre: str, fecha_inicio: str, fecha_fin: str,
                   descripcion: str = "", activa: bool = True) -> Dict:
    with _conn() as conn:
        cam_id = _next_id(conn, "campanas", "CAM")
        conn.execute("INSERT INTO campanas VALUES(?,?,?,?,?,?)",
                     (cam_id, nombre.strip(), fecha_inicio, fecha_fin, descripcion, int(activa)))
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM campanas WHERE id=?", (cam_id,)).fetchone())


def update_campana(campana_id: str, data: Dict) -> Optional[Dict]:
    allowed = {"nombre", "fecha_inicio", "fecha_fin", "descripcion", "activa", "meta"}
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return get_campana(campana_id)
    with _conn() as conn:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE campanas SET {sets} WHERE id=?", [*fields.values(), campana_id])
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM campanas WHERE id=?", (campana_id,)).fetchone())


def toggle_campana(campana_id: str, activa: bool) -> Optional[Dict]:
    with _conn() as conn:
        conn.execute("UPDATE campanas SET activa=? WHERE id=?", (int(activa), campana_id))
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM campanas WHERE id=?", (campana_id,)).fetchone())


# ── Centros ───────────────────────────────────────────────────────────────────

def _attach_campanas(conn: sqlite3.Connection, centro: Dict) -> Dict:
    rows = conn.execute("SELECT campana_id FROM centro_campanas WHERE centro_id=?", (centro["id"],)).fetchall()
    centro["campanas"] = [r[0] for r in rows]
    return centro


def get_centros() -> List[Dict]:
    with _conn() as conn:
        rows = _as_list(conn.execute("SELECT * FROM centros ORDER BY nombre").fetchall())
        return [_attach_campanas(conn, r) for r in rows]


def get_centro(centro_id: str) -> Optional[Dict]:
    with _conn() as conn:
        row = _as_dict(conn.execute("SELECT * FROM centros WHERE id=?", (centro_id,)).fetchone())
        return _attach_campanas(conn, row) if row else None


def create_centro(nombre: str, institucion: str, ubicacion: str,
                  encargado_id: Optional[str] = None,
                  campanas: Optional[List[str]] = None,
                  activo: bool = True,
                  lat: Optional[float] = None,
                  lng: Optional[float] = None,
                  cp: Optional[str] = None,
                  calle: Optional[str] = None,
                  colonia: Optional[str] = None,
                  ciudad: Optional[str] = None,
                  estado: Optional[str] = None) -> Dict:
    with _conn() as conn:
        c_id = _next_id(conn, "centros", "C")
        conn.execute("INSERT INTO centros VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (c_id, nombre.strip(), institucion.strip(), ubicacion.strip(),
                      encargado_id, int(activo), lat, lng, cp, calle, colonia, ciudad, estado))
        for cam in (campanas or []):
            conn.execute("INSERT OR IGNORE INTO centro_campanas VALUES(?,?)", (c_id, cam))
        conn.commit()
        return get_centro(c_id)


def update_centro(centro_id: str, data: Dict) -> Optional[Dict]:
    allowed = {"nombre", "institucion", "ubicacion", "encargado_id", "lat", "lng",
               "cp", "calle", "colonia", "ciudad", "estado"}
    fields = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if k in allowed and v is not None}
    with _conn() as conn:
        if fields:
            sets = ", ".join(f"{k}=?" for k in fields)
            conn.execute(f"UPDATE centros SET {sets} WHERE id=?", [*fields.values(), centro_id])
        if "campanas" in data:
            conn.execute("DELETE FROM centro_campanas WHERE centro_id=?", (centro_id,))
            for cam_id in (data["campanas"] or []):
                conn.execute("INSERT OR IGNORE INTO centro_campanas VALUES(?,?)", (centro_id, cam_id))
        conn.commit()
        return get_centro(centro_id)


def toggle_centro(centro_id: str, activo: bool) -> Optional[Dict]:
    with _conn() as conn:
        conn.execute("UPDATE centros SET activo=? WHERE id=?", (int(activo), centro_id))
        conn.commit()
        return get_centro(centro_id)


def add_centro_to_campana(centro_id: str, campana_id: str) -> Optional[Dict]:
    with _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO centro_campanas VALUES(?,?)", (centro_id, campana_id))
        conn.commit()
        return get_centro(centro_id)


def remove_centro_from_campana(centro_id: str, campana_id: str) -> Optional[Dict]:
    with _conn() as conn:
        conn.execute("DELETE FROM centro_campanas WHERE centro_id=? AND campana_id=?", (centro_id, campana_id))
        conn.commit()
        return get_centro(centro_id)


# ── Usuarios ──────────────────────────────────────────────────────────────────

VALID_ROLES   = {"coordinador_general","encargado_centro","voluntario","institucion_receptora","lider_campana"}
VALID_MOTIVOS = {"caducidad","daño","pérdida","corrección"}

def get_usuarios() -> List[Dict]:
    with _conn() as conn:
        return _as_list(conn.execute("SELECT * FROM usuarios ORDER BY nombre").fetchall())


def get_usuario(usuario_id: str) -> Optional[Dict]:
    with _conn() as conn:
        return _as_dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone())


def create_usuario(nombre: str, username: str, password: str, rol: str,
                   centro_id: Optional[str] = None, campana_id: Optional[str] = None,
                   institucion_id: Optional[str] = None) -> Dict:
    if rol not in VALID_ROLES:
        raise ValueError(f"Rol inválido: {rol}")
    with _conn() as conn:
        existing = conn.execute("SELECT id FROM usuarios WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if existing:
            raise ValueError(f"El nombre de usuario '{username}' ya existe.")
        u_id = _next_id(conn, "usuarios", "U")
        conn.execute("INSERT INTO usuarios VALUES(?,?,?,?,?,?,?,?,?)",
                     (u_id, nombre.strip(), username.strip(), password, rol,
                      centro_id or None, campana_id or None, institucion_id or None, 1))
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (u_id,)).fetchone())


def update_usuario(usuario_id: str, data: Dict) -> Optional[Dict]:
    allowed = {"nombre","username","password","rol","centro_id","campana_id","institucion_id","activo"}
    fields = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        if k == "rol" and v not in VALID_ROLES:
            raise ValueError(f"Rol inválido: {v}")
        fields[k] = v.strip() if isinstance(v, str) and k not in ("password",) else v
    if not fields:
        return get_usuario(usuario_id)
    with _conn() as conn:
        if "username" in fields:
            dup = conn.execute("SELECT id FROM usuarios WHERE username=? COLLATE NOCASE AND id!=?",
                               (fields["username"], usuario_id)).fetchone()
            if dup:
                raise ValueError(f"El nombre de usuario '{fields['username']}' ya existe.")
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE usuarios SET {sets} WHERE id=?", [*fields.values(), usuario_id])
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone())


def toggle_usuario(usuario_id: str, activo: bool) -> Optional[Dict]:
    with _conn() as conn:
        conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (int(activo), usuario_id))
        conn.commit()
        return _as_dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone())


def validate_login(username: str, password: str) -> Optional[Dict]:
    with _conn() as conn:
        return _as_dict(conn.execute(
            "SELECT * FROM usuarios WHERE username=? COLLATE NOCASE AND password=? AND activo=1",
            (username, password)).fetchone())


# ── Inventario — SQL view ─────────────────────────────────────────────────────

_INVENTARIO_SQL = """
SELECT
    a.id        AS articulo_id,
    a.nombre,
    a.categoria,
    a.unidad,
    COALESCE(SUM(
        CASE
            WHEN m.tipo = 'recepcion'             THEN  m.cantidad
            WHEN m.tipo = 'transferencia_entrada' THEN  m.cantidad
            WHEN m.tipo = 'ajuste' AND m.ajuste_tipo = 'positivo' THEN  m.cantidad
            WHEN m.tipo = 'ajuste' AND m.ajuste_tipo = 'negativo' THEN -m.cantidad
            WHEN m.tipo = 'ajuste'                THEN  m.cantidad
            WHEN m.tipo = 'merma' AND m.confirmado = 1 THEN -m.cantidad
            WHEN m.tipo = 'merma'                 THEN  0
            ELSE -m.cantidad
        END
    ), 0) AS stock
FROM articulos a
LEFT JOIN movimientos m
    ON m.articulo_id = a.id
    AND m.centro_id  = ?
    AND m.campana_id = ?
WHERE a.activo = 1
GROUP BY a.id, a.nombre, a.categoria, a.unidad
ORDER BY a.nombre
"""


def get_inventario(centro_id: str, campana_id: str) -> List[Dict]:
    with _conn() as conn:
        return [dict(r) for r in conn.execute(_INVENTARIO_SQL, (centro_id, campana_id)).fetchall()]


def get_stock(centro_id: str, campana_id: str, articulo_id: str) -> float:
    with _conn() as conn:
        return _stock(conn, centro_id, campana_id, articulo_id)


# ── Movimientos ───────────────────────────────────────────────────────────────

def get_movimientos(centro_id: Optional[str] = None,
                    campana_id: Optional[str] = None) -> List[Dict]:
    with _conn() as conn:
        q = "SELECT * FROM movimientos WHERE 1=1"
        p: list = []
        if centro_id:
            q += " AND centro_id=?"; p.append(centro_id)
        if campana_id:
            q += " AND campana_id=?"; p.append(campana_id)
        q += " ORDER BY fecha"
        rows = _as_list(conn.execute(q, p).fetchall())
        for r in rows:
            if r.get("donante") and isinstance(r["donante"], str):
                try:
                    r["donante"] = json.loads(r["donante"])
                except Exception:
                    pass
        return rows


def registrar_recepcion(centro_id, campana_id, articulo_id, cantidad,
                         actor_id, donante=None, observaciones="") -> Dict:
    with _conn() as conn:
        m = _insert_mov(conn, "recepcion", centro_id, campana_id, articulo_id,
                        cantidad, actor_id, donante=donante, observaciones=observaciones)
        conn.commit()
        return m


def registrar_entrega(centro_id, campana_id, articulo_id, cantidad, actor_id,
                       destino_id=None, institucion_receptora_id=None, observaciones="") -> Dict:
    with _conn() as conn:
        s = _stock(conn, centro_id, campana_id, articulo_id)
        if s < cantidad:
            raise ValueError(f"Stock insuficiente. Disponible: {s}")
        m = _insert_mov(conn, "entrega", centro_id, campana_id, articulo_id, cantidad, actor_id,
                        destino_id=destino_id, institucion_receptora_id=institucion_receptora_id,
                        observaciones=observaciones)
        conn.commit()
        return m


def registrar_merma(centro_id, campana_id, articulo_id, cantidad,
                     actor_id, motivo, observaciones="") -> Dict:
    if not motivo or motivo not in VALID_MOTIVOS:
        raise ValueError(f"Motivo obligatorio para merma. Opciones: {', '.join(sorted(VALID_MOTIVOS))}")
    with _conn() as conn:
        s = _stock(conn, centro_id, campana_id, articulo_id)
        if s < cantidad:
            raise ValueError(f"Stock insuficiente. Disponible: {s}")
        m = _insert_mov(conn, "merma", centro_id, campana_id, articulo_id, cantidad, actor_id,
                        motivo=motivo, observaciones=observaciones)
        conn.commit()
        return m


def registrar_transferencia(origen_id, destino_id, campana_id, articulo_id,
                              cantidad, actor_id, observaciones="") -> Dict:
    if origen_id == destino_id:
        raise ValueError("Origen y destino no pueden ser el mismo centro.")
    with _conn() as conn:
        s = _stock(conn, origen_id, campana_id, articulo_id)
        if s < cantidad:
            raise ValueError(f"Stock insuficiente en origen. Disponible: {s}")
        tr_id = f"TR{datetime.now().strftime('%Y%m%d%H%M%S')}"
        salida = _insert_mov(conn, "transferencia_salida", origen_id, campana_id, articulo_id,
                             cantidad, actor_id, destino_id=destino_id,
                             transferencia_id=tr_id, observaciones=observaciones)
        entrada = _insert_mov(conn, "transferencia_entrada", destino_id, campana_id, articulo_id,
                              cantidad, actor_id, destino_id=origen_id,
                              transferencia_id=tr_id, observaciones=observaciones)
        conn.commit()
        return {"transferencia_id": tr_id, "salida": salida, "entrada": entrada}


def registrar_ajuste(centro_id, campana_id, articulo_id, cantidad,
                      actor_id, tipo, motivo, observaciones="") -> Dict:
    if not motivo or motivo not in VALID_MOTIVOS:
        raise ValueError(f"Motivo obligatorio para ajuste. Opciones: {', '.join(sorted(VALID_MOTIVOS))}")
    with _conn() as conn:
        if tipo == "negativo":
            s = _stock(conn, centro_id, campana_id, articulo_id)
            if s < cantidad:
                raise ValueError(f"Stock insuficiente. Disponible: {s}")
        m = _insert_mov(conn, "ajuste", centro_id, campana_id, articulo_id, cantidad, actor_id,
                        ajuste_tipo=tipo, motivo=motivo, observaciones=observaciones)
        conn.commit()
        return m


def confirmar_movimiento(mov_id: str) -> Optional[Dict]:
    with _conn() as conn:
        conn.execute("UPDATE movimientos SET confirmado=1 WHERE id=?", (mov_id,))
        conn.commit()
        return _mov_dict(conn, mov_id)


# ── Instituciones ─────────────────────────────────────────────────────────────

def get_instituciones() -> List[Dict]:
    with _conn() as conn:
        return _as_list(conn.execute("SELECT * FROM instituciones").fetchall())


# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_db()

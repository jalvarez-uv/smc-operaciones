"""Gestor de persistencia SQLite3, esquema relacional, semilla de datos reales y CRUD."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union

from src.core.calculator import (
    calculate_operation_total_usd,
    calculate_total_time,
    normalize_time_str,
)
from src.core.models import (
    Cliente,
    DuplicateOrdenCompraError,
    DuplicateProformaError,
    Lancha,
    Operacion,
    OrdenCompraSummary,
    ProformaSummary,
    TarifaCliente,
    ValidationError,
)

SEED_CLIENTES: list[tuple[str, str, str, str, str]] = [
    (
        "LBH",
        "LBH Chile Ltda.",
        "Edgardo Mendoza",
        "edgardo.mendoza@lbhchile.com",
        "[+56] 9 4138 8805",
    ),
    (
        "CPT BOATS",
        "CPT Empresas Marítimas S.A.",
        "Operaciones CPT Iquique",
        "operaciones.iqq@cpt.cl",
        "[+56] 57 241 0000",
    ),
    (
        "IAN TAYLOR",
        "Empresas Taylor (Ian Taylor)",
        "Agencia Iquique",
        "agency.iqq@iantaylor.com",
        "[+56] 57 242 1500",
    ),
    (
        "BUCALEMU",
        "Servicios Marítimos Bucalemu",
        "Operaciones Bucalemu",
        "operaciones@bucalemu.cl",
        "[+56] 9 9000 1111",
    ),
    (
        "LORENA IQQ",
        "Agencia Marítima Lorena IQQ",
        "Contacto Operaciones",
        "contacto@lorenaiqq.cl",
        "[+56] 9 8000 2222",
    ),
]

SEED_TARIFAS: list[tuple[str, str, float]] = [
    ("LBH", "RECEPCIÓN", 650.00),
    ("LBH", "REGIMEN UP", 350.00),
    ("LBH", "REGIMEN OUT", 350.00),
    ("LBH", "SHIPCHANDLER", 330.00),
    ("LBH", "AMARRA", 460.00),
    ("LBH", "DESAMARRA", 460.00),
    ("LBH", "MANIOBRA ABORTADA", 300.00),
    ("CPT BOATS", "RECEPCIÓN", 350.00),
    ("CPT BOATS", "DESPACHO", 350.00),
    ("CPT BOATS", "REGIMEN UP", 200.00),
    ("CPT BOATS", "REGIMEN OUT", 200.00),
    ("CPT BOATS", "SHIPCHANDLER", 200.00),
    ("CPT BOATS", "AMARRA", 400.00),
    ("CPT BOATS", "DESAMARRA", 400.00),
    ("CPT BOATS", "MANIOBRA ABORTADA", 300.00),
    ("CPT BOATS", "RELEVO CONECTORES", 200.00),
    ("CPT BOATS", "RELEVO L/M", 200.00),
    ("IAN TAYLOR", "RECEPCIÓN", 500.00),
    ("IAN TAYLOR", "REGIMEN UP", 250.00),
    ("IAN TAYLOR", "REGIMEN OUT", 250.00),
    ("IAN TAYLOR", "SHIPCHANDLER", 180.00),
    ("IAN TAYLOR", "AMARRA", 455.00),
    ("IAN TAYLOR", "DESAMARRA", 455.00),
    ("BUCALEMU", "EMBARQUE DE ITO VETTING", 220.00),
    ("LORENA IQQ", "SHIPCHANDLER", 300.00),
]

DDL_STATEMENTS = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_agencia TEXT NOT NULL UNIQUE,
    razon_social TEXT NOT NULL,
    contacto_nombre TEXT DEFAULT '',
    email TEXT DEFAULT '',
    telefono TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tarifas_cliente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    servicio TEXT NOT NULL,
    valor_usd REAL NOT NULL CHECK (valor_usd >= 0),
    UNIQUE(cliente_id, servicio),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS proveedores_lancha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    rut TEXT DEFAULT '',
    contacto TEXT DEFAULT '',
    email TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS lanchas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    es_propia INTEGER NOT NULL CHECK (es_propia IN (0, 1)),
    proveedor_id INTEGER,
    tarifa_costo_base_usd REAL DEFAULT 0.0,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores_lancha(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS operaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    hrs_inicio TEXT NOT NULL,
    hrs_termino TEXT NOT NULL,
    total_time TEXT NOT NULL,
    nave TEXT NOT NULL,
    cliente TEXT NOT NULL,
    servicio TEXT NOT NULL,
    terminal TEXT DEFAULT '',
    lancha TEXT NOT NULL,
    valor_usd REAL NOT NULL DEFAULT 0.0,
    extra_usd REAL NOT NULL DEFAULT 0.0,
    total_usd REAL NOT NULL DEFAULT 0.0,
    observaciones TEXT DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
    proforma_smc TEXT DEFAULT '',
    oc_cte TEXT DEFAULT '',
    factura_smc TEXT DEFAULT '',
    lbh_agenciamiento TEXT DEFAULT '',
    oc_proveedor_folio TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_operaciones_fecha ON operaciones(fecha);
CREATE INDEX IF NOT EXISTS idx_operaciones_cliente_nave ON operaciones(cliente, nave);
CREATE INDEX IF NOT EXISTS idx_operaciones_lancha ON operaciones(lancha);
CREATE INDEX IF NOT EXISTS idx_operaciones_estado ON operaciones(estado);
CREATE INDEX IF NOT EXISTS idx_operaciones_proforma ON operaciones(proforma_smc);

CREATE TABLE IF NOT EXISTS proformas (
    folio TEXT PRIMARY KEY,
    fecha_emision TEXT NOT NULL,
    cliente TEXT NOT NULL,
    nave_nombre TEXT NOT NULL,
    nave_clasificacion TEXT DEFAULT 'M/N',
    valor_dolar_clp REAL NOT NULL DEFAULT 980.0,
    descuento_usd REAL NOT NULL DEFAULT 0.0,
    subtotal_usd REAL NOT NULL,
    iva_usd REAL NOT NULL,
    otros_usd REAL NOT NULL DEFAULT 0.0,
    total_usd REAL NOT NULL,
    observaciones TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS ordenes_compra (
    folio_oc TEXT PRIMARY KEY,
    fecha_emision TEXT NOT NULL,
    proveedor_nombre TEXT NOT NULL,
    lancha_nombre TEXT NOT NULL,
    subtotal_usd REAL NOT NULL,
    iva_usd REAL NOT NULL,
    total_usd REAL NOT NULL,
    observaciones TEXT DEFAULT ''
);
"""


class DatabaseManager:
    """Administrador de base de datos SQLite3 para SMC-Operaciones."""

    def __init__(self, db_path: Union[Path, str] = Path("data/smc_operaciones.db")) -> None:
        self.is_memory = str(db_path) == ":memory:"
        self.db_path = Path(db_path) if not self.is_memory else Path(":memory:")
        self._memory_conn: Optional[sqlite3.Connection] = None

        if not self.is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self.is_memory:
            assert self._memory_conn is not None
            try:
                yield self._memory_conn
                self._memory_conn.commit()
            except Exception:
                self._memory_conn.rollback()
                raise
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def close(self) -> None:
        """Cierra la conexión persistente si se usa base de datos en memoria."""
        if self._memory_conn is not None:
            self._memory_conn.close()
            self._memory_conn = None

    def init_db(self) -> None:
        """Crea el esquema de tablas e índices y ejecuta la semilla inicial."""
        with self._connection() as conn:
            conn.executescript(DDL_STATEMENTS)
        self.seed_initial_data()

    def seed_initial_data(self) -> None:
        """Precarga clientes, tarifarios reales en USD, proveedor y lanchas de forma idempotente."""
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO clientes
                    (codigo_agencia, razon_social, contacto_nombre, email, telefono)
                VALUES (?, ?, ?, ?, ?)
                """,
                SEED_CLIENTES,
            )

            cursor = conn.execute("SELECT id, codigo_agencia FROM clientes")
            client_ids = {row["codigo_agencia"]: row["id"] for row in cursor.fetchall()}

            tariff_rows = [
                (client_ids[codigo], servicio, valor_usd)
                for codigo, servicio, valor_usd in SEED_TARIFAS
                if codigo in client_ids
            ]
            conn.executemany(
                """
                INSERT OR IGNORE INTO tarifas_cliente (cliente_id, servicio, valor_usd)
                VALUES (?, ?, ?)
                """,
                tariff_rows,
            )

            provider_name = "Servicios Marítimos Bucalemu / Armador Externo"
            conn.execute(
                """
                INSERT OR IGNORE INTO proveedores_lancha (nombre, rut, contacto, email)
                VALUES (?, '', 'Armador Externo', '')
                """,
                (provider_name,),
            )
            prov_row = conn.execute(
                "SELECT id FROM proveedores_lancha WHERE nombre = ?",
                (provider_name,),
            ).fetchone()
            prov_id = prov_row["id"] if prov_row else None

            conn.execute(
                """
                INSERT OR IGNORE INTO lanchas (nombre, es_propia, proveedor_id, tarifa_costo_base_usd)
                VALUES ('DOÑA RENATA', 1, NULL, 0.0)
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO lanchas (nombre, es_propia, proveedor_id, tarifa_costo_base_usd)
                VALUES ('BUCA LAUREL', 0, ?, 200.0)
                """,
                (prov_id,),
            )

    @staticmethod
    def _prepare_operacion(op: Operacion) -> Operacion:
        """Normaliza horarios y recalcula TOTAL TIME y TOTAL USD antes de persistir."""
        ini = normalize_time_str(op.hrs_inicio)
        fin = normalize_time_str(op.hrs_termino)
        tt = calculate_total_time(ini, fin)
        total_usd = calculate_operation_total_usd(op.valor_usd, op.extra_usd)

        return Operacion(
            id=op.id,
            fecha=op.fecha.strip(),
            hrs_inicio=ini,
            hrs_termino=fin,
            total_time=tt,
            nave=op.nave.strip().upper(),
            cliente=op.cliente.strip().upper(),
            servicio=op.servicio.strip().upper(),
            terminal=op.terminal.strip().upper(),
            lancha=op.lancha.strip().upper(),
            valor_usd=float(op.valor_usd or 0.0),
            extra_usd=float(op.extra_usd or 0.0),
            total_usd=total_usd,
            observaciones=op.observaciones.strip(),
            estado=(op.estado or "PENDIENTE").strip().upper(),
            proforma_smc=op.proforma_smc.strip(),
            oc_cte=op.oc_cte.strip(),
            factura_smc=op.factura_smc.strip(),
            lbh_agenciamiento=op.lbh_agenciamiento.strip(),
            oc_proveedor_folio=op.oc_proveedor_folio.strip(),
        )

    @staticmethod
    def _row_to_operacion(row: sqlite3.Row) -> Operacion:
        return Operacion(
            id=row["id"],
            fecha=row["fecha"],
            hrs_inicio=row["hrs_inicio"],
            hrs_termino=row["hrs_termino"],
            total_time=row["total_time"],
            nave=row["nave"],
            cliente=row["cliente"],
            servicio=row["servicio"],
            terminal=row["terminal"],
            lancha=row["lancha"],
            valor_usd=row["valor_usd"],
            extra_usd=row["extra_usd"],
            total_usd=row["total_usd"],
            observaciones=row["observaciones"],
            estado=row["estado"],
            proforma_smc=row["proforma_smc"],
            oc_cte=row["oc_cte"],
            factura_smc=row["factura_smc"],
            lbh_agenciamiento=row["lbh_agenciamiento"],
            oc_proveedor_folio=row["oc_proveedor_folio"],
        )

    def create_operacion(self, op: Operacion) -> int:
        """Inserta una nueva maniobra y retorna su ID asignado."""
        clean = self._prepare_operacion(op)
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO operaciones (
                    fecha, hrs_inicio, hrs_termino, total_time, nave, cliente,
                    servicio, terminal, lancha, valor_usd, extra_usd, total_usd,
                    observaciones, estado, proforma_smc, oc_cte, factura_smc,
                    lbh_agenciamiento, oc_proveedor_folio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean.fecha,
                    clean.hrs_inicio,
                    clean.hrs_termino,
                    clean.total_time,
                    clean.nave,
                    clean.cliente,
                    clean.servicio,
                    clean.terminal,
                    clean.lancha,
                    clean.valor_usd,
                    clean.extra_usd,
                    clean.total_usd,
                    clean.observaciones,
                    clean.estado,
                    clean.proforma_smc,
                    clean.oc_cte,
                    clean.factura_smc,
                    clean.lbh_agenciamiento,
                    clean.oc_proveedor_folio,
                ),
            )
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    def update_operacion(self, op_id: int, op: Operacion) -> None:
        """Actualiza una maniobra existente recalculando TT y TOTAL USD."""
        clean = self._prepare_operacion(op)
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE operaciones SET
                    fecha = ?, hrs_inicio = ?, hrs_termino = ?, total_time = ?,
                    nave = ?, cliente = ?, servicio = ?, terminal = ?, lancha = ?,
                    valor_usd = ?, extra_usd = ?, total_usd = ?, observaciones = ?,
                    estado = ?, proforma_smc = ?, oc_cte = ?, factura_smc = ?,
                    lbh_agenciamiento = ?, oc_proveedor_folio = ?
                WHERE id = ?
                """,
                (
                    clean.fecha,
                    clean.hrs_inicio,
                    clean.hrs_termino,
                    clean.total_time,
                    clean.nave,
                    clean.cliente,
                    clean.servicio,
                    clean.terminal,
                    clean.lancha,
                    clean.valor_usd,
                    clean.extra_usd,
                    clean.total_usd,
                    clean.observaciones,
                    clean.estado,
                    clean.proforma_smc,
                    clean.oc_cte,
                    clean.factura_smc,
                    clean.lbh_agenciamiento,
                    clean.oc_proveedor_folio,
                    op_id,
                ),
            )

    def delete_operacion(self, op_id: int) -> None:
        """Elimina una maniobra por su ID."""
        with self._connection() as conn:
            conn.execute("DELETE FROM operaciones WHERE id = ?", (op_id,))

    def get_operacion(self, op_id: int) -> Optional[Operacion]:
        """Obtiene una maniobra por su ID."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM operaciones WHERE id = ?", (op_id,)).fetchone()
            return self._row_to_operacion(row) if row else None

    def list_operaciones(
        self,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        nave: Optional[str] = None,
        cliente: Optional[str] = None,
        lancha: Optional[str] = None,
        estado: Optional[str] = None,
        solo_sin_proforma: bool = False,
        solo_lancha_externa_pendiente_oc: bool = False,
    ) -> list[Operacion]:
        """Lista maniobras aplicando filtros combinables."""
        query = "SELECT o.* FROM operaciones o WHERE 1=1"
        params: list[object] = []

        if fecha_desde:
            query += " AND o.fecha >= ?"
            params.append(fecha_desde.strip())
        if fecha_hasta:
            query += " AND o.fecha <= ?"
            params.append(fecha_hasta.strip())
        if nave:
            query += " AND UPPER(o.nave) LIKE ?"
            params.append(f"%{nave.strip().upper()}%")
        if cliente:
            query += " AND UPPER(o.cliente) = ?"
            params.append(cliente.strip().upper())
        if lancha:
            query += " AND UPPER(o.lancha) = ?"
            params.append(lancha.strip().upper())
        if estado:
            query += " AND UPPER(o.estado) = ?"
            params.append(estado.strip().upper())
        if solo_sin_proforma:
            query += " AND (o.proforma_smc IS NULL OR TRIM(o.proforma_smc) = '')"
        if solo_lancha_externa_pendiente_oc:
            query += (
                " AND EXISTS (SELECT 1 FROM lanchas l WHERE UPPER(l.nombre) = UPPER(o.lancha) AND l.es_propia = 0)"
                " AND (o.oc_proveedor_folio IS NULL OR TRIM(o.oc_proveedor_folio) = '')"
            )

        query += " ORDER BY o.fecha ASC, o.hrs_inicio ASC, o.id ASC"

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_operacion(r) for r in rows]

    def bulk_insert_operaciones(
        self, operaciones: list[Operacion], clear_existing: bool = False
    ) -> int:
        """Inserta múltiples maniobras en una sola transacción."""
        cleaned = [self._prepare_operacion(op) for op in operaciones]
        with self._connection() as conn:
            if clear_existing:
                conn.execute("DELETE FROM operaciones")
            conn.executemany(
                """
                INSERT INTO operaciones (
                    fecha, hrs_inicio, hrs_termino, total_time, nave, cliente,
                    servicio, terminal, lancha, valor_usd, extra_usd, total_usd,
                    observaciones, estado, proforma_smc, oc_cte, factura_smc,
                    lbh_agenciamiento, oc_proveedor_folio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c.fecha,
                        c.hrs_inicio,
                        c.hrs_termino,
                        c.total_time,
                        c.nave,
                        c.cliente,
                        c.servicio,
                        c.terminal,
                        c.lancha,
                        c.valor_usd,
                        c.extra_usd,
                        c.total_usd,
                        c.observaciones,
                        c.estado,
                        c.proforma_smc,
                        c.oc_cte,
                        c.factura_smc,
                        c.lbh_agenciamiento,
                        c.oc_proveedor_folio,
                    )
                    for c in cleaned
                ],
            )
        return len(cleaned)

    def get_suggested_tariff(self, cliente_codigo: str, servicio: str) -> Optional[float]:
        """Retorna el valor sugerido en USD según la matriz Cliente + Servicio."""
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT t.valor_usd
                FROM tarifas_cliente t
                JOIN clientes c ON c.id = t.cliente_id
                WHERE UPPER(c.codigo_agencia) = ? AND UPPER(t.servicio) = ?
                """,
                (cliente_codigo.strip().upper(), servicio.strip().upper()),
            ).fetchone()
            return float(row["valor_usd"]) if row else None

    def upsert_tariff(self, cliente_codigo: str, servicio: str, valor_usd: float) -> None:
        """Crea o actualiza la tarifa base en USD para un cliente y tipo de servicio."""
        codigo = cliente_codigo.strip().upper()
        serv = servicio.strip().upper()
        val = float(valor_usd)
        if val < 0:
            raise ValueError("El valor de tarifa USD no puede ser negativo.")

        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM clientes WHERE UPPER(codigo_agencia) = ?",
                (codigo,),
            ).fetchone()
            if not row:
                raise ValueError(f"Cliente '{codigo}' no encontrado.")
            cliente_id = row["id"]
            conn.execute(
                """
                INSERT INTO tarifas_cliente (cliente_id, servicio, valor_usd)
                VALUES (?, ?, ?)
                ON CONFLICT(cliente_id, servicio) DO UPDATE SET valor_usd = excluded.valor_usd
                """,
                (cliente_id, serv, val),
            )

    def list_tariffs(self, cliente_codigo: Optional[str] = None) -> list[TarifaCliente]:
        """Lista las tarifas configuradas, opcionalmente filtradas por cliente."""
        query = """
            SELECT t.id, t.cliente_id, c.codigo_agencia, t.servicio, t.valor_usd
            FROM tarifas_cliente t
            JOIN clientes c ON c.id = t.cliente_id
        """
        params: list[object] = []
        if cliente_codigo:
            query += " WHERE UPPER(c.codigo_agencia) = ?"
            params.append(cliente_codigo.strip().upper())
        query += " ORDER BY c.codigo_agencia ASC, t.servicio ASC"

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                TarifaCliente(
                    id=r["id"],
                    cliente_id=r["cliente_id"],
                    codigo_agencia=r["codigo_agencia"],
                    servicio=r["servicio"],
                    valor_usd=float(r["valor_usd"]),
                )
                for r in rows
            ]

    def list_clientes(self) -> list[Cliente]:
        """Lista todas las agencias navieras registradas."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM clientes ORDER BY codigo_agencia ASC").fetchall()
            return [
                Cliente(
                    id=r["id"],
                    codigo_agencia=r["codigo_agencia"],
                    razon_social=r["razon_social"],
                    contacto_nombre=r["contacto_nombre"],
                    email=r["email"],
                    telefono=r["telefono"],
                )
                for r in rows
            ]

    def get_cliente_by_codigo(self, codigo_agencia: str) -> Optional[Cliente]:
        """Obtiene un cliente por su código de agencia."""
        with self._connection() as conn:
            r = conn.execute(
                "SELECT * FROM clientes WHERE UPPER(codigo_agencia) = ?",
                (codigo_agencia.strip().upper(),),
            ).fetchone()
            if not r:
                return None
            return Cliente(
                id=r["id"],
                codigo_agencia=r["codigo_agencia"],
                razon_social=r["razon_social"],
                contacto_nombre=r["contacto_nombre"],
                email=r["email"],
                telefono=r["telefono"],
            )

    def list_lanchas(self, solo_externas: bool = False) -> list[Lancha]:
        """Lista las lanchas portuarias, opcionalmente solo las externas/arrendadas."""
        query = """
            SELECT l.id, l.nombre, l.es_propia, p.nombre AS proveedor_nombre, l.tarifa_costo_base_usd
            FROM lanchas l
            LEFT JOIN proveedores_lancha p ON p.id = l.proveedor_id
        """
        if solo_externas:
            query += " WHERE l.es_propia = 0"
        query += " ORDER BY l.es_propia DESC, l.nombre ASC"

        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
            return [
                Lancha(
                    id=r["id"],
                    nombre=r["nombre"],
                    es_propia=bool(r["es_propia"]),
                    proveedor_nombre=r["proveedor_nombre"],
                    tarifa_costo_base_usd=float(r["tarifa_costo_base_usd"]),
                )
                for r in rows
            ]

    def get_operations_summary(self) -> dict[str, list[dict[str, object]]]:
        """Retorna estadísticas agregadas de operaciones por Cliente, Servicio y Lancha."""
        with self._connection() as conn:
            por_cliente = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT cliente, COUNT(*) AS cantidad, ROUND(SUM(total_usd), 2) AS total_usd
                    FROM operaciones
                    GROUP BY cliente
                    ORDER BY total_usd DESC
                    """
                ).fetchall()
            ]
            por_servicio = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT servicio, COUNT(*) AS cantidad, ROUND(SUM(total_usd), 2) AS total_usd
                    FROM operaciones
                    GROUP BY servicio
                    ORDER BY cantidad DESC
                    """
                ).fetchall()
            ]
            por_lancha = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT lancha, COUNT(*) AS cantidad, ROUND(SUM(total_usd), 2) AS total_usd
                    FROM operaciones
                    GROUP BY lancha
                    ORDER BY cantidad DESC
                    """
                ).fetchall()
            ]
        return {
            "por_cliente": por_cliente,
            "por_servicio": por_servicio,
            "por_lancha": por_lancha,
        }

    def register_proforma(
        self,
        proforma: ProformaSummary,
        operation_ids: list[int],
        force_reissue: bool = False,
    ) -> None:
        """Registra una Proforma y actualiza proforma_smc y estado='AGENCIA' en las maniobras.

        Lanza DuplicateProformaError si alguna maniobra ya posee proforma_smc asignado
        y force_reissue es False (CP-09).
        """
        if not operation_ids:
            raise ValidationError("Debe seleccionar al menos una maniobra para emitir la Proforma.")

        folio_clean = proforma.folio.strip()
        if not folio_clean:
            raise ValidationError("El folio de la Proforma no puede estar vacío.")

        placeholders = ",".join("?" for _ in operation_ids)
        with self._connection() as conn:
            rows = conn.execute(
                f"SELECT id, proforma_smc FROM operaciones WHERE id IN ({placeholders})",
                operation_ids,
            ).fetchall()

            if len(rows) != len(set(operation_ids)):
                raise ValidationError("Una o más maniobras seleccionadas no existen en la base de datos.")

            if not force_reissue:
                conflicts = {
                    int(r["id"]): str(r["proforma_smc"]).strip()
                    for r in rows
                    if r["proforma_smc"] and str(r["proforma_smc"]).strip()
                }
                if conflicts:
                    folios_str = ", ".join(sorted(set(conflicts.values())))
                    raise DuplicateProformaError(
                        f"Las maniobras seleccionadas ya poseen Proforma asignada ({folios_str}).",
                        conflicting_folios=conflicts,
                    )

                existing_folio = conn.execute(
                    "SELECT folio FROM proformas WHERE folio = ?",
                    (folio_clean,),
                ).fetchone()
                if existing_folio:
                    raise DuplicateProformaError(
                        f"El folio de Proforma '{folio_clean}' ya se encuentra registrado."
                    )

            conn.execute(
                """
                INSERT OR REPLACE INTO proformas (
                    folio, fecha_emision, cliente, nave_nombre, nave_clasificacion,
                    valor_dolar_clp, descuento_usd, subtotal_usd, iva_usd, otros_usd,
                    total_usd, observaciones
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    folio_clean,
                    proforma.fecha_emision.strip(),
                    proforma.cliente.codigo_agencia.strip().upper(),
                    proforma.nave_nombre.strip().upper(),
                    proforma.nave_clasificacion.strip(),
                    float(proforma.valor_dolar_clp),
                    float(proforma.descuento_usd),
                    float(proforma.subtotal_usd),
                    float(proforma.iva_usd),
                    float(proforma.otros_usd),
                    float(proforma.total_usd),
                    proforma.observaciones.strip(),
                ),
            )

            conn.execute(
                f"""
                UPDATE operaciones
                SET proforma_smc = ?,
                    estado = CASE WHEN UPPER(estado) = 'FACTURA' THEN 'FACTURA' ELSE 'AGENCIA' END
                WHERE id IN ({placeholders})
                """,
                [folio_clean, *operation_ids],
            )

    def register_orden_compra(
        self,
        oc: OrdenCompraSummary,
        operation_ids: list[int],
        force_reissue: bool = False,
    ) -> None:
        """Registra una Orden de Compra para lancha externa y marca oc_proveedor_folio."""
        if not operation_ids:
            raise ValidationError("Debe seleccionar al menos una maniobra para emitir la Orden de Compra.")

        folio_clean = oc.folio_oc.strip()
        if not folio_clean:
            raise ValidationError("El folio de la Orden de Compra no puede estar vacío.")

        placeholders = ",".join("?" for _ in operation_ids)
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.id, o.lancha, o.oc_proveedor_folio, l.es_propia
                FROM operaciones o
                LEFT JOIN lanchas l ON UPPER(l.nombre) = UPPER(o.lancha)
                WHERE o.id IN ({placeholders})
                """,
                operation_ids,
            ).fetchall()

            if len(rows) != len(set(operation_ids)):
                raise ValidationError("Una o más maniobras seleccionadas no existen en la base de datos.")

            for r in rows:
                if r["es_propia"] == 1:
                    raise ValidationError(
                        f"La maniobra ID {r['id']} fue ejecutada por lancha propia ({r['lancha']}) "
                        "y no corresponde a una Orden de Compra a proveedor externo."
                    )

            if not force_reissue:
                conflicts = {
                    int(r["id"]): str(r["oc_proveedor_folio"]).strip()
                    for r in rows
                    if r["oc_proveedor_folio"] and str(r["oc_proveedor_folio"]).strip()
                }
                if conflicts:
                    folios_str = ", ".join(sorted(set(conflicts.values())))
                    raise DuplicateOrdenCompraError(
                        f"Las maniobras seleccionadas ya poseen Orden de Compra asignada ({folios_str}).",
                        conflicting_folios=conflicts,
                    )

            conn.execute(
                """
                INSERT OR REPLACE INTO ordenes_compra (
                    folio_oc, fecha_emision, proveedor_nombre, lancha_nombre,
                    subtotal_usd, iva_usd, total_usd, observaciones
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    folio_clean,
                    oc.fecha_emision.strip(),
                    oc.proveedor_nombre.strip(),
                    oc.lancha_nombre.strip().upper(),
                    float(oc.subtotal_usd),
                    float(oc.iva_usd),
                    float(oc.total_usd),
                    oc.observaciones.strip(),
                ),
            )

            conn.execute(
                f"UPDATE operaciones SET oc_proveedor_folio = ? WHERE id IN ({placeholders})",
                [folio_clean, *operation_ids],
            )



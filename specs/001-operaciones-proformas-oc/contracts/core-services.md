# Phase 1: Core Library & UI Interface Contracts

**Feature**: `001-operaciones-proformas-oc`
**Date**: 2026-11-13
**Architecture**: Clean Modular Python 3.11+ (`src/core/` decoupled from `src/ui/`)

---

## 1. Contrato de Modelos de Dominio (`src/core/models.py`)

Entidades inmutables o validadas mediante `dataclasses` / `pydantic`:

- **`Operacion`**:
  - Campos correspondientes a las 18 columnas de `Control de Operaciones Iquique.xlsx` más `id: Optional[int]` y `oc_proveedor_folio: str`.
- **`Cliente`**:
  - `id: Optional[int]`, `codigo_agencia: str`, `razon_social: str`, `contacto_nombre: str`, `email: str`, `telefono: str`.
- **`TarifaCliente`**:
  - `id: Optional[int]`, `cliente_id: int`, `codigo_agencia: str`, `servicio: str`, `valor_usd: float`.
- **`Lancha`**:
  - `id: Optional[int]`, `nombre: str`, `es_propia: bool`, `proveedor_nombre: Optional[str]`, `tarifa_costo_base_usd: float`.
- **`ProformaSummary`**:
  - `folio: str`, `fecha_emision: str`, `cliente: Cliente`, `nave_nombre: str`, `nave_clasificacion: str`, `valor_dolar_clp: float`, `operaciones: list[Operacion]`, `descuento_usd: float`, `subtotal_usd: float`, `iva_usd: float`, `otros_usd: float`, `total_usd: float`, `total_clp_referencial: float`.
- **`OrdenCompraSummary`**:
  - `folio_oc: str`, `fecha_emision: str`, `proveedor_nombre: str`, `lancha_nombre: str`, `operaciones: list[Operacion]`, `subtotal_usd: float`, `iva_usd: float`, `total_usd: float`, `observaciones: str`.

---

## 2. Contrato de Calculadora de Tiempos, Tarifas e Impuestos (`src/core/calculator.py`)

Funciones puras sin efectos secundarios (100% testables en `tests/test_calculator.py`):

```python
def calculate_total_time(hrs_inicio: str, hrs_termino: str) -> str:
    """
    Calcula la duración efectiva (TT) entre hrs_inicio y hrs_termino en formato 'HH:MM:SS'.
    Si hrs_termino < hrs_inicio (cruce de medianoche, ej. 23:30:00 a 00:45:00),
    suma 24 horas automáticamente devolviendo '01:15:00'.
    Lanza ValueError si el formato horario es inválido.
    """

def format_tt_short(total_time: str) -> str:
    """
    Convierte '00:35:00' a formato corto de Proforma '0:35:00'.
    """

def calculate_operation_total_usd(
    valor_usd: float,
    extra_usd: float = 0.0,
    descuento_usd: float = 0.0,
) -> float:
    """
    Retorna round((valor_usd + extra_usd) - descuento_usd, 2).
    """

def calculate_proforma_totals(
    line_amounts_usd: list[float],
    descuento_usd: float = 0.0,
    otros_usd: float = 0.0,
    iva_rate: float = 0.19,
    valor_dolar_clp: float = 981.08,
) -> dict[str, float]:
    """
    Calcula:
      - subtotal_usd: round(sum(line_amounts_usd) - descuento_usd, 2)
      - iva_usd: round(subtotal_usd * iva_rate, 2)
      - total_usd: round(subtotal_usd + iva_usd + otros_usd, 2)
      - total_usd_rounded: round(total_usd)
      - total_clp: round(total_usd * valor_dolar_clp)
    """

def build_proforma_line_description(fecha: str, hrs_inicio: str, hrs_termino: str, total_time: str) -> str:
    """
    Construye la glosa oficial de Proforma SMC:
    'DD/MM/YYYY        HH:MM:SS    a    HH:MM:SS    TT:    H:MM:SS'
    """
```

---

## 3. Contrato de Base de Datos y Repositorio (`src/core/database.py`)

Clase `DatabaseManager(db_path: Path | str)`:

- **Inicialización y Semilla**:
  - `init_db() -> None`: Crea tablas e índices si no existen y ejecuta `seed_initial_data()`.
  - `seed_initial_data() -> None`: Inserta de forma idempotente los 5 clientes (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`), sus 25 tarifarios reales en USD, y las lanchas `DOÑA RENATA` (propia) y `BUCA LAUREL` (externa).
- **Gestión de Operaciones (CRUD & Filtros)**:
  - `create_operacion(op: Operacion) -> int`
  - `update_operacion(op_id: int, op: Operacion) -> None`
  - `delete_operacion(op_id: int) -> None`
  - `get_operacion(op_id: int) -> Optional[Operacion]`
  - `list_operaciones(fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None, nave: Optional[str] = None, cliente: Optional[str] = None, lancha: Optional[str] = None, estado: Optional[str] = None, solo_sin_proforma: bool = False, solo_lancha_externa_pendiente_oc: bool = False) -> list[Operacion]`
  - `bulk_insert_operaciones(operaciones: list[Operacion], clear_existing: bool = False) -> int`
- **Gestión de Tarifarios y Catálogos**:
  - `get_suggested_tariff(cliente_codigo: str, servicio: str) -> Optional[float]`
  - `upsert_tariff(cliente_codigo: str, servicio: str, valor_usd: float) -> None`
  - `list_tariffs(cliente_codigo: Optional[str] = None) -> list[TarifaCliente]`
  - `list_clientes() -> list[Cliente]`
  - `get_cliente_by_codigo(codigo_agencia: str) -> Optional[Cliente]`
  - `list_lanchas(solo_externas: bool = False) -> list[Lancha]`
- **Emisión y Prevención de Doble Cobro / Pago**:
  - `register_proforma(proforma: ProformaSummary, operation_ids: list[int], force_reissue: bool = False) -> None`:
    - Verifica si alguna operación en `operation_ids` ya posee `proforma_smc` no vacío. Si lo posee y `force_reissue=False`, lanza `DuplicateProformaError` indicando los IDs/folios en conflicto (cumpliendo **CP-09**).
    - Registra la cabecera en `proformas` y actualiza `proforma_smc = proforma.folio` y `estado = 'AGENCIA'` en todas las operaciones seleccionadas dentro de una transacción atómica.
  - `register_orden_compra(oc: OrdenCompraSummary, operation_ids: list[int], force_reissue: bool = False) -> None`:
    - Verifica que las operaciones pertenezcan a lanchas externas y no posean `oc_proveedor_folio` previo (salvo `force_reissue=True`).
    - Registra la Orden de Compra en `ordenes_compra` y marca `oc_proveedor_folio = oc.folio_oc` en las operaciones incluidas.
- **Métricas y Resumen**:
  - `get_operations_summary() -> dict`: Retorna conteos y montos USD acumulados por Cliente, por Tipo de Servicio y por Lancha (propia vs. externa).

---

## 4. Contrato de Servicio Excel (`src/core/excel_service.py`)

- `import_operations_from_excel(file_path: Path) -> list[Operacion]`:
  - Lee la hoja `CONTROL OPES` de `Control de Operaciones Iquique.xlsx`.
  - Mapea las 18 columnas estándar desde la fila 4 en adelante.
  - Descarta filas vacías al final del libro que solo contienen fórmulas en cero (`00:00:00` o `$0`), retornando las 476 operaciones reales (**CP-08**).
- `export_operations_to_excel(operaciones: list[Operacion], output_path: Path) -> Path`:
  - Genera un libro `.xlsx` con el encabezado corporativo `PLANILLA CONTROL DE OPERACIONES IQUIQUE` y las 18 columnas oficiales formateadas.
- `generate_proforma_excel(proforma: ProformaSummary, output_path: Path) -> Path`:
  - Genera el archivo `.xlsx` de **Proforma de Servicios** replicando el diseño exacto de SMC (bloques `CLIENTE`, `NAVE`, `DETALLES DEL SERVICIO`, tabla `TIPO SERVICIO | DESCRIPCIÓN | CANTIDAD | PRECIO | Dcto | TOTAL AMOUNT`, bloque `CONDICIONES DE SERVICIO - OBSERVACIONES` con `Valor Dolar`, `Subtotal`, `IVA 19%`, `TOTAL`) sin filas residuales (**CP-06**).
- `generate_orden_compra_excel(oc: OrdenCompraSummary, output_path: Path) -> Path`:
  - Genera el archivo `.xlsx` de **Orden de Compra a Proveedor de Lancha Externa** con el desglose de maniobras (Fecha, Horario, `TT`, Nave atendida, Servicio, Lancha, Costo Unitario USD, Total USD), Subtotal, IVA 19% y Total (**CP-07**).

---

## 5. Contrato de Servicio PDF (`src/core/pdf_service.py`)

- `generate_proforma_pdf(proforma: ProformaSummary, output_path: Path) -> Path`:
  - Genera el documento PDF corporativo de **Proforma de Servicios** con membrete SMC (`77.000.970-7`), folio, datos del cliente y de la nave, tabla de maniobras valorizadas en USD, tipo de cambio referencial, Subtotal, IVA (19%) y Total USD.
- `generate_orden_compra_pdf(oc: OrdenCompraSummary, output_path: Path) -> Path`:
  - Genera el documento PDF corporativo de **Orden de Compra** dirigido al proveedor de la lancha externa (ej. `BUCA LAUREL`), detallando las maniobras liquidadas y los totales a pagar.

---

## 6. Contrato de Interfaz Gráfica (`src/ui/app.py`)

Ventana principal `SMCOperacionesApp(ctk.CTk)` con `CTkTabview` de 4 pestañas:

1. **Pestaña 1: `Control de Operaciones`**:
   - Formulario superior/lateral para crear/editar maniobra con cálculo en vivo de `TOTAL TIME` y autocompletado de `VALOR USD` al elegir `CLIENTE` + `SERVICIO`.
   - Barra de filtros por Fecha, Nave, Cliente, Lancha y Estado.
   - Tabla (`Treeview`) con las 18 columnas de la bitácora.
   - Botones de acción: *Guardar*, *Actualizar*, *Eliminar*, *Importar Excel Base*, *Exportar Vista a Excel*.
2. **Pestaña 2: `Emitir Proforma de Servicios`**:
   - Selectores de `Cliente` (ej. `LBH`), `Nave` (ej. `SHUN XING 17`) y filtro de fechas.
   - Tabla de maniobras seleccionables con alerta visual si alguna ya tiene folio asignado.
   - Campos de emisión: `Folio Proforma` (autocompletado sugerido `SMC-PDS-IQQ-[CLIENTE]-V[XXXX]`), `Fecha Emisión`, `Clasificación Nave`, `Valor Dólar CLP`, `Descuento USD`.
   - Panel de totales en vivo (`Subtotal USD`, `IVA 19% USD`, `Total USD`, `Total CLP ref.`).
   - Botón *Emitir Proforma (Excel + PDF)* que genera ambos documentos y marca las operaciones en la base de datos.
3. **Pestaña 3: `Emitir Orden de Compra (OC Lanchas)`**:
   - Selector de `Lancha Externa` (ej. `BUCA LAUREL`) y rango de fechas (ej. `21/10/2026`).
   - Tabla de maniobras ejecutadas por dicha lancha externa pendientes de pago a proveedor.
   - Campos de emisión: `Folio OC` (`SMC-OC-IQQ-BL-V001`), `Proveedor`, `Tarifa Costo USD`.
   - Panel de totales de costo y botón *Emitir Orden de Compra (Excel + PDF)*.
4. **Pestaña 4: `Tarifarios y Resumen`**:
   - Sub-panel izquierdo: Gestión CRUD del tarifario en USD por `(Cliente, Servicio)` y catálogo de lanchas.
   - Sub-panel derecho: Tarjetas de KPIs y tablas de resumen de operaciones y facturación agrupadas por Cliente, por Tipo de Servicio y por Lancha (`DOÑA RENATA` vs `BUCA LAUREL`).


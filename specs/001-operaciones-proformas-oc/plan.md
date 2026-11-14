# Implementation Plan: SMC Operaciones — Control de Operaciones, Proformas de Servicio y Órdenes de Compra

**Branch**: `001-operaciones-proformas-oc` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-operaciones-proformas-oc/spec.md`

---

## Summary

Implementar el sistema completo **SMC-Operaciones** para **Servicios Marítimos Carrere (SMC)** bajo una arquitectura modular en Python 3.11+ donde toda la lógica de dominio, persistencia SQLite3 (`src/core/database.py`), entidades (`src/core/models.py`), motor de cálculo de horarios con cruce de medianoche e impuestos (`src/core/calculator.py`), importación/exportación Excel (`src/core/excel_service.py` con `openpyxl`) y generación de PDFs corporativos (`src/core/pdf_service.py` con `ReportLab`) residen desacoplados en `src/core/`, expuestos a través de una interfaz gráfica de escritorio moderna en `CustomTkinter` (`src/ui/app.py`) organizada en 4 pestañas operativas:
1. **Control de Operaciones** (CRUD de 18 columnas, filtros dinámicos, cálculo automático de `TOTAL TIME` y `TOTAL USD`, importación/exportación compatible con `Control de Operaciones Iquique.xlsx`).
2. **Emitir Proforma de Servicios** (pre-factura por Cliente + Nave con tarifarios reales en USD, IVA 19%, tipo de cambio Dólar Observado, foliado único `SMC-PDS-IQQ-[CLIENTE]-V[XXXX]`, exportación `.xlsx` + `.pdf` y bloqueo de doble cobro).
3. **Emitir Orden de Compra (OC Lanchas)** (liquidación de pagos para lanchas externas/subcontratadas como `BUCA LAUREL`, exportación `.xlsx` + `.pdf`).
4. **Tarifarios y Resumen** (catálogo de precios por cliente/servicio y panel estadístico de operaciones).

---

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `customtkinter==6.0.0`, `openpyxl==3.1.5`, `reportlab==5.1.0`, `pydantic==2.14.3` (y `sqlite3` / `pathlib` / `dataclasses` de la librería estándar)

**Storage**: SQLite 3 local embebido (`data/smc_operaciones.db`) con sincronización bidireccional a archivos Excel (`.xlsx`) y exportación documental en `data/export/`

**Testing**: `pytest==9.2.0` (`tests/test_calculator.py` y `tests/test_excel_import_export.py` cubriendo los casos **CP-01** a **CP-09** de `docs/PLAN_DE_PRUEBAS.md`)

**Target Platform**: Multiplataforma Linux (Linux Mint / Ubuntu para desarrollo) y Windows 10/11 (ejecución desde código fuente y ejecutable portable `.exe` vía PyInstaller en GitHub Actions)

**Project Type**: Librería de dominio integrable (`src/core/`) + Aplicación de escritorio GUI (`src/ui/`)

**Performance Goals**:
- Generación de archivos Excel (`.xlsx`) y PDF (`.pdf`) de Proformas y Órdenes de Compra en $< 3\text{ segundos}$ (objetivo real $< 0.5\text{ segundos}$).
- Importación íntegra de las 476 operaciones históricas en $< 2\text{ segundos}$.
- Filtrado interactivo en grilla de operaciones en $< 100\text{ ms}$.

**Constraints**:
- Respeto estricto a las 18 columnas de `Control de Operaciones Iquique.xlsx`.
- Cero dependencias de interfaz gráfica dentro de `src/core/`.
- Uso exclusivo de `pathlib.Path` y codificación `UTF-8` explícita en todas las operaciones de E/S.

**Scale/Scope**: ~500 a 5,000 maniobras anuales por puerto, 5 agencias navieras principales precargadas (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`), 25 tarifas base en USD y flota mixta (`DOÑA RENATA` propia, `BUCA LAUREL` externa).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked and verified after Phase 1 design.*

| Principio Constitucional | Estado Pre-Diseño | Estado Post-Diseño | Evidencia de Cumplimiento en el Plan |
| :--- | :---: | :---: | :--- |
| **I. Arquitectura Limpia y Modular en Python 3.11+ (`src/core/` vs `src/ui/`)** | PASS | PASS | `src/core/` contiene `models.py`, `calculator.py`, `database.py`, `excel_service.py` y `pdf_service.py` sin importar `tkinter`/`customtkinter`. `src/ui/app.py` solo consume contratos de `src/core/`. |
| **II. Fidelidad Absoluta a Datos y Formatos Reales de SMC** | PASS | PASS | Se preservan las 18 columnas exactas de `Control de Operaciones Iquique.xlsx`, los tarifarios reales de las 5 agencias, el formato oficial de Proforma (`SMC-PDS-IQQ-[CLIENTE]-V[XXXX]`) y la OC para `BUCA LAUREL`. |
| **III. Desarrollo Guiado por Pruebas (TDD con `pytest`)** | PASS | PASS | Diseño guiado por los 9 casos de prueba de `docs/PLAN_DE_PRUEBAS.md` (**CP-01** a **CP-09**) implementados en `tests/test_calculator.py` y `tests/test_excel_import_export.py`. |
| **IV. Portabilidad Multiplataforma Linux y Windows** | PASS | PASS | Rutas gestionadas con `pathlib.Path`, SQLite3 nativo, `openpyxl` y `ReportLab` 100% Python multiplataforma y codificación `UTF-8`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-operaciones-proformas-oc/
├── plan.md              # Este plan técnico de implementación
├── research.md          # Decisiones arquitectónicas y técnicas (Phase 0)
├── data-model.md        # Esquema SQLite, ERD y Seed Data de SMC (Phase 1)
├── quickstart.md        # Guía de ejecución y validación de pruebas (Phase 1)
├── contracts/
│   └── core-services.md # Contratos de interfaz de src/core/ y src/ui/ (Phase 1)
└── tasks.md             # Lista secuencial de tareas (/speckit-tasks - Phase 2)
```

### Source Code (repository root)

```text
smc-operaciones/
├── data/
│   ├── Control de Operaciones Iquique.xlsx
│   ├── Copia de Proforma de Servicios IQQ 29OCT26 SMC- LBH6526 - SHUN XING 17.xlsx
│   ├── smc_operaciones.db          # Base de datos SQLite local (autogenerada + seed)
│   └── export/                     # Carpeta de salida por defecto para Proformas y OC (.xlsx y .pdf)
├── docs/
│   ├── SRS.md
│   ├── PLAN_DE_PRUEBAS.md
│   └── GUIA_ANTIGRAVITY_SPECKIT.md
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py               # Dataclasses/Modelos: Operacion, Cliente, TarifaCliente, Lancha, ProformaSummary, OrdenCompraSummary
│   │   ├── calculator.py           # Cálculo de TOTAL TIME (con cruce de medianoche), TOTAL USD, Subtotal, IVA 19% y glosas
│   │   ├── database.py             # Gestor SQLite3, DDL, Seed de tarifarios/clientes/lanchas, CRUD, filtros y prevención de doble cobro
│   │   ├── excel_service.py        # Importador de las 476 maniobras y generador .xlsx de Bitácora, Proformas y Órdenes de Compra
│   │   └── pdf_service.py          # Generador .pdf corporativo de Proformas de Servicio y Órdenes de Compra con ReportLab
│   └── ui/
│       ├── __init__.py
│       └── app.py                  # Aplicación CustomTkinter con 4 pestañas operativas
└── tests/
    ├── __init__.py
    ├── test_calculator.py          # Pruebas unitarias CP-01, CP-02, CP-03 y cálculos de IVA/Proforma
    └── test_excel_import_export.py # Pruebas de integración y aceptación CP-04 a CP-09 (SHUN XING 17, BUCA LAUREL, 476 filas, doble cobro)
```

**Structure Decision**: Se adopta la estructura modular de proyecto único con separación estricta entre `src/core/` (librería de dominio y persistencia) y `src/ui/` (capa de presentación CustomTkinter), alineada con `docs/SRS.md`, `README.md` y el Principio I de la Constitución.

---

## Detailed Component Design

### 1. Modelos de Dominio (`src/core/models.py`)
Define las estructuras de datos tipadas y excepciones de negocio (`DuplicateProformaError`, `DuplicateOrdenCompraError`, `ValidationError`):
- `Operacion`: Representa una fila de la bitácora con sus 18 atributos oficiales (`fecha`, `hrs_inicio`, `hrs_termino`, `total_time`, `nave`, `cliente`, `servicio`, `terminal`, `lancha`, `valor_usd`, `extra_usd`, `total_usd`, `observaciones`, `estado`, `proforma_smc`, `oc_cte`, `factura_smc`, `lbh_agenciamiento`) más `id` y `oc_proveedor_folio`.
- `Cliente`, `TarifaCliente`, `Lancha`, `ProformaSummary`, `OrdenCompraSummary`.

### 2. Motor de Cálculo y Tarifarios (`src/core/calculator.py`)
- **`calculate_total_time(hrs_inicio, hrs_termino)`**:
  - Parsea cadenas `HH:MM:SS` o `HH:MM` (u objetos `datetime.time` provenientes de Excel).
  - Si `termino_seg < inicio_seg`, suma `86400` segundos ($24\text{ h}$) para resolver el cruce de medianoche (**CP-01**, **CP-02**).
  - Retorna formato `HH:MM:SS` (ej. `01:15:00`).
- **`calculate_operation_total_usd(valor_usd, extra_usd, descuento_usd=0.0)`**:
  - Retorna `round(float(valor_usd) + float(extra_usd or 0.0) - float(descuento_usd or 0.0), 2)` (**CP-03**).
- **`calculate_proforma_totals(line_amounts_usd, descuento_usd=0.0, otros_usd=0.0, iva_rate=0.19, valor_dolar_clp=981.08)`**:
  - Calcula `subtotal_usd`, `iva_usd` ($19\%$), `total_usd`, `total_usd_rounded` y `total_clp` (**CP-06**).

### 3. Persistencia SQLite y Semilla Real (`src/core/database.py`)
- Crea automáticamente el esquema relacional detallado en [data-model.md](data-model.md).
- Ejecuta `seed_initial_data()` insertando de forma idempotente:
  - **Clientes**: `LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ` con sus contactos comerciales reales.
  - **Lanchas**: `DOÑA RENATA` (`es_propia = 1`) y `BUCA LAUREL` (`es_propia = 0`, asociada al proveedor externo con tarifa costo base de `$200.00 USD`).
  - **Tarifarios Reales (`tarifas_cliente`)**: Las 25 combinaciones `(Cliente, Servicio)` extraídas de la operación real de Iquique (incluyendo `LBH + RECEPCIÓN = 650.00`, `LBH + REGIMEN UP/OUT = 350.00`, `LBH + SHIPCHANDLER = 330.00`, `CPT BOATS + RECEPCIÓN = 350.00`, `CPT BOATS + REGIMEN UP/OUT = 200.00`, etc.).
- Gestiona la emisión transaccional de Proformas (`register_proforma`) validando que ninguna maniobra posea un folio previo en `proforma_smc` (**CP-09**), y la emisión de Órdenes de Compra (`register_orden_compra`).

### 4. Servicio Excel (`src/core/excel_service.py`)
- **`import_operations_from_excel`**: Abre `Control de Operaciones Iquique.xlsx` (`data_only=True`), recorre desde la fila 4 de la hoja `CONTROL OPES`, normaliza fechas (`YYYY-MM-DD`) y horas (`HH:MM:SS`), recalcula `total_time` y `total_usd` cuando sea necesario, e ignora las filas inferiores vacías que solo tienen fórmulas en cero, importando exactamente las **476 maniobras válidas** (**CP-08**).
- **`generate_proforma_excel`**: Construye un archivo `.xlsx` con el diseño exacto de la Proforma de Servicios de SMC (`PROFORMA DE SERVICIOS`, datos de `California 5, Cerro Alegre / Iquique`, RUT `77.000.970-7`, bloques `CLIENTE`, `NAVE`, `DETALLES DEL SERVICIO`, tabla de maniobras con únicamente las filas de la nave seleccionada sin basura de otras naves, y bloque inferior con `Valor Dolar`, `Subtotal`, `IVA 19%` y `TOTAL`) (**CP-06**).
- **`generate_orden_compra_excel`**: Construye el libro `.xlsx` de Orden de Compra para el proveedor de la lancha externa (ej. `BUCA LAUREL`), listando las maniobras filtradas (ej. las 6 maniobras del `21/10/2026` para `RONG HENG 68` y `HUA YING 66`), su costo unitario, Subtotal, IVA y Total (**CP-07**).

### 5. Servicio PDF Corporativo (`src/core/pdf_service.py`)
- **`generate_proforma_pdf`** y **`generate_orden_compra_pdf`**: Generan documentos PDF tamaño Carta con `ReportLab` incluyendo encabezado institucional de Servicios Marítimos Carrere, tablas con bordes y colores corporativos (azul marino `#1B365D` y gris claro `#F2F4F8`), glosas detalladas de horarios y `TT`, cuadro de observaciones y desglose financiero en USD y CLP.

### 6. Interfaz Gráfica en CustomTkinter (`src/ui/app.py`)
Implementa `SMCOperacionesApp` con barra superior institucional y un `CTkTabview` con las 4 pestañas requeridas:
1. **`1. Control de Operaciones`**: Formulario de registro/edición con cálculo instantáneo de `TOTAL TIME` y `TOTAL USD`, autocompletado de tarifa según `CLIENTE + SERVICIO`, filtros combinables (`Fecha`, `Nave`, `Cliente`, `Lancha`, `Estado`), tabla `Treeview` de 18 columnas y botones de importación/exportación de la planilla base.
2. **`2. Emitir Proforma de Servicios`**: Filtro por `Cliente` y `Nave`, selección de maniobras pendientes, configuración de `Folio` (`SMC-PDS-IQQ-...`), `Valor Dólar Observado`, cálculo en vivo de `Subtotal USD`, `IVA 19%` y `Total USD`, validación contra doble facturación y exportación dual a `.xlsx` y `.pdf`.
3. **`3. Emitir Orden de Compra (OC Lanchas)`**: Filtro específico para lanchas externas (`BUCA LAUREL`), selección de maniobras por fecha, ajuste de tarifa de costo por maniobra y generación de la Orden de Compra en `.xlsx` y `.pdf`.
4. **`4. Tarifarios y Resumen`**: Editor de la matriz de tarifarios por cliente y panel de resumen ejecutivo con totales de maniobras e ingresos en USD desglosados por Cliente, Tipo de Servicio y Lancha (`DOÑA RENATA` vs `BUCA LAUREL`).

---

## Complexity Tracking

> **No existen violaciones a la Constitución.** La arquitectura mantiene 0 dependencias cruzadas de UI en `src/core/`, usa exclusivamente librerías multiplataforma puras y cubre todos los casos del plan de pruebas.

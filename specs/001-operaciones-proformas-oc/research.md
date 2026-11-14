# Phase 0: Technical Research & Architectural Decisions

**Feature**: `001-operaciones-proformas-oc`
**Date**: 2026-11-13
**Status**: Completed (0 unknowns remaining)

---

## 1. Arquitectura Desacoplada (`src/core/` vs `src/ui/`)

- **Decision**: Implementar una arquitectura de capas limpias donde `src/core/` concentra el 100% de las reglas de negocio, persistencia SQLite, cálculos aritméticos/horarios y generación documental (`.xlsx` y `.pdf`), sin ninguna importación ni dependencia de `customtkinter` o `tkinter`.
- **Rationale**: Cumple con el Principio I de la Constitución. Permite ejecutar toda la suite de pruebas automatizadas (`pytest`) en entornos headless (como GitHub Actions) y garantiza que `src/core/` pueda integrarse directamente como librería en el ERP corporativo de Servicios Marítimos Carrere o ejecutarse desde la app de escritorio (`src/ui/app.py`).
- **Alternatives considered**:
  - *Lógica embebida en callbacks de UI*: Descartada por impedir pruebas unitarias aisladas y violar la constitución del proyecto.
  - *Arquitectura cliente-servidor web (FastAPI + React)*: Descartada para el MVP dado que el requerimiento operativo en Iquique exige una aplicación local autocontenida y compilable a `.exe` portable sin servidores externos.

---

## 2. Cálculo de Duración (`TOTAL TIME`) con Cruce de Medianoche

- **Decision**: Normalizar `HRS INICIO` y `HRS TERMINO` a segundos o minutos desde las `00:00:00`. Si $\text{segundos}(\text{HRS TERMINO}) < \text{segundos}(\text{HRS INICIO})$, sumar $86\,400\text{ segundos}$ ($24\text{ horas}$) al término antes de restar, formateando la salida como `HH:MM:SS` (y `H:MM:SS` en la glosa de Proforma).
- **Rationale**: En operaciones portuarias reales de SMC, las maniobras nocturnas frecuentemente inician antes de las `00:00` y terminan en la madrugada siguiente (ej. `23:30:00` a `00:45:00` $\rightarrow$ `01:15:00`). El objeto `datetime.time` de Python no soporta resta directa; convertir a `timedelta` con ajuste de $+24\text{h}$ resuelve todos los casos borde sin valores negativos.
- **Alternatives considered**:
  - *Exigir fecha+hora completa en ambos campos*: Descartado porque la planilla histórica `Control de Operaciones Iquique.xlsx` posee una sola columna `FECHA` y dos columnas de hora (`HRS INICIO`, `HRS TERMINO`).

---

## 3. Importación y Exportación de Excel (`openpyxl`)

- **Decision**: Utilizar `openpyxl` en modo lectura de valores (`data_only=True`) para la importación de `Control de Operaciones Iquique.xlsx` (hoja `CONTROL OPES`, encabezados en fila 3, datos desde fila 4) y descartar filas donde `NAVE`, `CLIENTE` y `SERVICIO` sean simultáneamente vacíos/nulos (ignorando filas finales que solo contienen fórmulas `00:00:00` o `$0`). Para la exportación de Proformas y Órdenes de Compra, generar libros `.xlsx` con estilos corporativos y fórmulas vivas (`=SUM(...)`, `=Subtotal*0.19`).
- **Rationale**: La inspección del archivo real en `data/Control de Operaciones Iquique.xlsx` confirmó exactamente 476 maniobras válidas y decenas de filas inferiores con fórmulas pre-arrastradas en cero. Asimismo, el archivo testigo `Copia de Proforma de Servicios IQQ 29OCT26 SMC- LBH6526 - SHUN XING 17.xlsx` requiere preservar la estructura visual de encabezado (Cliente, Nave, Detalles del Servicio) y tabla de cobro sin filas residuales de otras naves.
- **Alternatives considered**:
  - *Uso exclusivo de `pandas.read_excel`*: Aunque útil para análisis tabular, `openpyxl` ofrece control exacto sobre celdas combinadas, formatos de moneda/hora, fórmulas vivas y estilos de bordes requeridos en las Proformas y Órdenes de Compra.

---

## 4. Generación de PDF Corporativo (`ReportLab`)

- **Decision**: Construir el servicio `src/core/pdf_service.py` utilizando `reportlab.platypus` (`SimpleDocTemplate`, `Table`, `TableStyle`, `Paragraph`, `Spacer`) en tamaño Carta (`letter`), replicando el diseño oficial de SMC: membrete con RUT `77.000.970-7`, dirección en Valparaíso/Iquique, bloques de Cliente y Nave, tabla de maniobras con glosa `DD/MM/YYYY HH:MM:SS a HH:MM:SS TT: H:MM:SS`, recuadro de condiciones con Valor Dólar Observado y desglose de Subtotal USD, IVA (19%) y Total USD.
- **Rationale**: `ReportLab` es 100% puro Python, multiplataforma (Linux y Windows), no requiere motores externos (como `wkhtmltopdf` o `GTK/Cairo` de `WeasyPrint` que fallan al empaquetar en `.exe` para Windows) y genera documentos PDF en menos de 0.2 segundos.
- **Alternatives considered**:
  - *WeasyPrint / wkhtmltopdf*: Descartados por requerir librerías binarias del sistema operativo que rompen el Principio IV de portabilidad en Windows.

---

## 5. Persistencia SQLite3 y Semilla de Datos Reales (Seed)

- **Decision**: Implementar `src/core/database.py` sobre la librería estándar `sqlite3` con `PRAGMA foreign_keys = ON`, almacenando la base de datos en `data/smc_operaciones.db` (o en ruta configurable vía `pathlib.Path` / `:memory:` para tests). Al inicializar la base de datos por primera vez, ejecutar una semilla idempotente (`seed_initial_data`) con:
  1. Los 5 clientes reales (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`) y sus datos de contacto.
  2. La matriz real de tarifarios en USD por `(Cliente, Servicio)` extraída de la operación histórica de Iquique.
  3. Las 2 lanchas del catálogo (`DOÑA RENATA` como flota propia de SMC y `BUCA LAUREL` como lancha externa/arrendada vinculada a su proveedor).
- **Rationale**: Garantiza que el sistema sea inmediatamente operativo tras su instalación, autocompletando tarifas y clasificando lanchas sin configuración manual previa.
- **Alternatives considered**:
  - *Archivos JSON sueltos*: Descartados por carecer de integridad referencial, transacciones atómicas para el foliado de Proformas/OC y consultas filtradas eficientes.

---

## 6. Interfaz Gráfica de Usuario (`CustomTkinter` + `ttk.Treeview`)

- **Decision**: Implementar `src/ui/app.py` empleando `CustomTkinter` (`CTk`, `CTkTabview`, `CTkFrame`, `CTkEntry`, `CTkComboBox`, `CTkButton`) estructurado en 4 pestañas principales:
  1. **Control de Operaciones** (CRUD, autocompletado de tarifa y TT, filtros dinámicos, importación/exportación Excel).
  2. **Emitir Proforma de Servicios** (selección de Cliente + Nave, previsualización de maniobras pendientes, ingreso de Folio y Valor Dólar, cálculo de IVA 19%, emisión `.xlsx` + `.pdf` y bloqueo de doble cobro).
  3. **Emitir Orden de Compra (OC Lanchas)** (filtrado automático de maniobras ejecutadas por lanchas externas como `BUCA LAUREL`, ajuste/verificación de costos y emisión de OC en `.xlsx` + `.pdf`).
  4. **Tarifarios y Resumen** (administración de la matriz tarifaria por cliente y KPIs/resumen estadístico por cliente, servicio y lancha equivalente a `GRAFICO X SERVICIOS`).
- **Rationale**: Combina la estética moderna y soporte de temas de `CustomTkinter` con el rendimiento de `ttk.Treeview` para renderizar cientos de maniobras de forma instantánea.


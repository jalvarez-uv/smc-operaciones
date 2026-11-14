# Phase 1: Quickstart & Validation Guide

**Feature**: `001-operaciones-proformas-oc`
**Date**: 2026-11-13
**Reference Contracts**: [core-services.md](contracts/core-services.md) | [data-model.md](data-model.md)

---

## 1. Prerrequisitos y Entorno

- **Python**: `3.11+`
- **Entorno Virtual**: `.venv` configurado en la raíz del repositorio.
- **Archivos de Datos Reales**:
  - `data/Control de Operaciones Iquique.xlsx` (476 operaciones históricas).
  - `data/Copia de Proforma de Servicios IQQ 29OCT26 SMC- LBH6526 - SHUN XING 17.xlsx` (documento testigo de referencia).

### Activación del Entorno

En **Linux Mint / Ubuntu**:
```bash
source .venv/bin/activate
```

En **Windows (PowerShell)**:
```powershell
.venv\Scripts\activate
```

---

## 2. Ejecución de la Suite de Pruebas Automatizadas (TDD)

Para validar todos los casos de prueba definidos en `docs/PLAN_DE_PRUEBAS.md` (**CP-01** a **CP-09**):

```bash
pytest -v
```

### Resultados Esperados de Validación Automatizada
1. **`tests/test_calculator.py`**:
   - **CP-01**: `09:15:00` a `09:45:00` $\rightarrow$ `00:30:00`.
   - **CP-02**: Cruce de medianoche `23:30:00` a `00:45:00` $\rightarrow$ `01:15:00` (positivo).
   - **CP-03**: Valor base `$330.00` + Extra `$330.00` $\rightarrow$ Total `$660.00`.
2. **`tests/test_excel_import_export.py`**:
   - **CP-04 & CP-05**: Semilla de tarifarios sugiere `$650.00` para `(LBH, RECEPCIÓN)` y `$350.00` para `(CPT BOATS, RECEPCIÓN)`.
   - **CP-06**: Generación de Proforma real para *SHUN XING 17* (`29/10/2026`, cliente `LBH`, 5 maniobras) produce `.xlsx` y `.pdf` con `Subtotal = 2030.00 USD`, `IVA (19%) = 385.70 USD` y `Total = 2415.70 USD`.
   - **CP-07**: Generación de Orden de Compra para lancha externa *BUCA LAUREL* (`21/10/2026`) filtra exactamente las 6 maniobras de las naves `RONG HENG 68` y `HUA YING 66` excluyendo maniobras de `DOÑA RENATA`.
   - **CP-08**: Importación de `data/Control de Operaciones Iquique.xlsx` carga exactamente las 476 operaciones reales e ignora filas vacías con fórmulas en cero.
   - **CP-09**: Intentar emitir una segunda Proforma sobre operaciones ya marcadas con folio `SMC-PDS-IQQ-LBH-V6526` lanza `DuplicateProformaError`.

---

## 3. Ejecución de la Aplicación de Escritorio (`CustomTkinter`)

```bash
python -m src.ui.app
```

### Flujo de Verificación Manual en las 4 Pestañas
1. **Pestaña `Control de Operaciones`**:
   - Hacer clic en **Importar Excel Base** y seleccionar `data/Control de Operaciones Iquique.xlsx` (si no se ha importado aún). Verificar que se listan las 476 operaciones con sus 18 columnas.
   - Seleccionar cliente `LBH` y servicio `RECEPCIÓN` en el formulario y comprobar que `VALOR USD` se autocompleta en `650.00`.
   - Ingresar `23:30:00` y `00:45:00` y verificar que `TOTAL TIME` muestra `01:15:00`.
2. **Pestaña `Emitir Proforma de Servicios`**:
   - Filtrar por Cliente `LBH` y Nave `SHUN XING 17`.
   - Verificar las 5 maniobras del `29/10/2026`, el cálculo de `Subtotal: $2,030.00 USD`, `IVA 19%: $385.70 USD` y `Total: $2,415.70 USD`.
   - Presionar **Emitir Proforma (Excel + PDF)** y comprobar los archivos generados en `data/export/`.
3. **Pestaña `Emitir Orden de Compra (OC Lanchas)`**:
   - Seleccionar la lancha externa `BUCA LAUREL` y fecha `2026-10-21`.
   - Verificar que aparecen las 6 maniobras de `RONG HENG 68` y `HUA YING 66`.
   - Presionar **Emitir Orden de Compra (Excel + PDF)** y comprobar los archivos generados en `data/export/`.
4. **Pestaña `Tarifarios y Resumen`**:
   - Revisar la tabla de tarifarios precargados (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`) y el panel de métricas operativas por cliente, servicio y lancha.


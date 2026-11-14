<!--
=== Sync Impact Report ===
Version change: Template (Unratified) → 1.0.0
Modified principles:
  - [PRINCIPLE_1_NAME] → I. Arquitectura Limpia y Modular en Python 3.11+ (Desacoplamiento Core / UI)
  - [PRINCIPLE_2_NAME] → II. Fidelidad Absoluta a los Datos y Formatos Reales de Servicios Marítimos Carrere (SMC)
  - [PRINCIPLE_3_NAME] → III. Desarrollo Guiado por Pruebas (TDD con pytest - NO NEGOCIABLE)
  - [PRINCIPLE_4_NAME] → IV. Portabilidad Multiplataforma Linux y Windows
Removed sections:
  - [PRINCIPLE_5_NAME] (consolidado en los 4 principios definidos)
Added sections:
  - Restricciones Técnicas y Estándares de Datos (Section 2)
  - Flujo de Desarrollo y Criterios de Calidad (Section 3)
Deferred items / TODOs:
  - None (todos los marcadores resueltos)
==========================
-->

# SMC-Operaciones Constitution

## Core Principles

### I. Arquitectura Limpia y Modular en Python 3.11+ (Desacoplamiento Core / UI)
Toda la lógica de negocio, acceso a la base de datos SQLite, cálculo de tiempos/tarifas y generación de documentos Excel/PDF DEBE residir exclusivamente en `src/core/`. El paquete `src/core/` DEBE ser completamente autónomo e independiente de cualquier biblioteca gráfica, permitiendo que el sistema funcione tanto como ejecutable de escritorio portable (.exe compilado con PyInstaller) como una librería integrable en el ERP o ecosistema de software corporativo de SMC. La interfaz gráfica (`src/ui/` construida con CustomTkinter) actuará estrictamente como capa de presentación y consumo de los servicios de `src/core/`.

### II. Fidelidad Absoluta a los Datos y Formatos Reales de Servicios Marítimos Carrere (SMC)
El sistema DEBE respetar y reproducir con exactitud la estructura de 18 columnas de la bitácora `Control de Operaciones Iquique.xlsx`, los tarifarios comerciales en USD diferenciados por cliente (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`), el formato corporativo de Proforma de Servicios (incluyendo foliado oficial `SMC-PDS-IQQ-[CLIENTE]-V[XXXX]`, cálculo de IVA al 19% y desglose de maniobras) y el flujo de generación de Órdenes de Compra para liquidar servicios ejecutados por lanchas subcontratadas/arrendadas (ej. `BUCA LAUREL`). Ninguna simplificación técnica puede alterar las reglas de facturación o la coherencia documental histórica de la empresa.

### III. Desarrollo Guiado por Pruebas (TDD con pytest - NO NEGOCIABLE)
Todo cálculo matemático, de duración temporal y financiero DEBE estar validado mediante pruebas automatizadas en `tests/` antes de su implementación definitiva (ciclo Red-Green-Refactor), de acuerdo con la matriz de validación definida en `docs/PLAN_DE_PRUEBAS.md`. Es mandatorio cubrir y validar:
- Cálculo de `TOTAL TIME` diurno y con cruce de medianoche (sin duraciones negativas ni desbordes).
- Aplicación de tarifario base en USD por cliente/servicio, recargos horarios (`EXTRA USD`), descuentos y cálculo de IVA (19%).
- Prevención de doble cobro/facturación y filtrado estricto de maniobras por lancha y nave.
- El 100% de la suite de pruebas unitarias e integración debe ejecutarse exitosamente en verde tanto en entornos locales Linux como en el flujo de integración continua de Windows (`windows-latest`).

### IV. Portabilidad Multiplataforma Linux y Windows
El código fuente DEBE ejecutarse de forma transparente y sin adaptaciones manuales tanto en Linux Mint / Ubuntu (entorno de desarrollo) como en Windows 10/11 (entorno productivo de SMC). Para garantizar esto:
- Es OBLIGATORIO utilizar `pathlib.Path` para toda manipulación y resolución de rutas de archivos, prohibiendo rutas fijas o concatenaciones con separadores de sistema operativo (`/` o `\`).
- Todos los archivos leídos o generados (código fuente, SQLite, Excel, JSON, texto) DEBEN especificar explícitamente codificación `UTF-8`.
- No se permiten llamadas directas al sistema operativo dependientes de plataforma (`os.system`) ni librerías binarias exclusivas de un único SO en `src/core/`.

## Restricciones Técnicas y Estándares de Datos

- **Stack Oficial:** Python 3.11+, SQLite3 embebido, `openpyxl` (plantillas Excel con fórmulas vivas), `ReportLab` (generación de PDF corporativos oficiales), `CustomTkinter` (UI de escritorio moderna) y `pytest` (suite de pruebas).
- **Persistencia Local Autocontenida:** Los datos operativos residen en SQLite local (`data/smc_operaciones.db`) con soporte nativo de importación y exportación bidireccional desde y hacia planillas `.xlsx`.
- **Integridad Financiera y Trazabilidad:** Cada maniobra cuenta con campos de auditoría y vinculación (`PROFORMA SMC`, `OC CTE`, `FACTURA`, `ESTADO`) para impedir cobros duplicados y asegurar trazabilidad entre la bitácora operativa y la liquidación contable.
- **Rendimiento Documental:** La generación de archivos Excel y PDF de Proforma y Órdenes de Compra debe ejecutarse en menos de 3 segundos por documento.

## Flujo de Desarrollo y Criterios de Calidad

- **Metodología Spec-Driven Development:** Todo cambio arquitectónico o nueva funcionalidad debe orquestarse mediante el flujo de Spec Kit (`.specify/` y `specs/`), manteniendo consistencia entre especificación (`spec.md`), plan (`plan.md`) y tareas (`tasks.md`).
- **Control de Calidad y Criterios de Aceptación:**
  1. Cobertura completa de pruebas en `tests/` aprobadas al 100% con `pytest -v`.
  2. Adherencia estricta a PEP 8 y tipado estático gradual con type hints.
  3. Verificación de compilación y empaquetado portable en GitHub Actions (`build-windows.yml`).

## Governance

- La presente constitución es el documento supremo de gobernanza técnica y funcional del proyecto SMC-Operaciones.
- Prevalece sobre cualquier requerimiento informal, preferencia personal o atajo técnico de desarrollo.
- **Procedimiento de Enmienda:** Cualquier modificación a estos principios debe documentarse formalmente, justificarse en base a requerimientos de operación de Servicios Marítimos Carrere y someterse a versionamiento semántico.
- **Política de Versionamiento Semántico:**
  - **MAJOR:** Remoción, redefinición o cambio incompatible de principios fundamentales.
  - **MINOR:** Incorporación de nuevos principios o expansión sustancial de directrices técnicas.
  - **PATCH:** Clarificaciones, correcciones ortográficas o refinamientos no semánticos de redacción.
- **Verificación de Cumplimiento:** Todos los pull requests, revisiones de código y sesiones de trabajo con agentes inteligentes (Antigravity / Spec Kit) deben verificar explícitamente el cumplimiento de estos principios antes de considerar completada cualquier tarea.

**Version**: 1.0.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13

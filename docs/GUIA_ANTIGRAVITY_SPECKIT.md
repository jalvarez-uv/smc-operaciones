# Guía Paso a Paso: Cómo trabajar en Antigravity con Spec Kit, Modelos recomendados y Git

---

## 1. Diagnóstico de tu Carpeta (¿Hiciste bien al mover `.agents` y `.specify`?)

**¡Sí, hiciste 100% bien!**  
Cuando ejecutas `specify init smc-operaciones` estando ya dentro de `smc-operaciones` (en vez de usar `specify init .` o `--here`), la herramienta crea una subcarpeta con ese nombre. Al cortar `.agents` y `.specify` y pegarlos en la raíz de tu proyecto, dejaste la estructura exactamente como **Antigravity (`agy`)** la necesita:
- `.agents/workflows/` contiene los comandos slash (`/speckit.constitution`, `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`).
- `.specify/` contiene las plantillas, memoria y scripts bash que ejecutará el agente.

### ⚠️ Dos verificaciones rápidas antes de abrir Antigravity:

1. **Verifica la carpeta oculta `.git`:**  
   En tu captura de pantalla se ven las carpetas ocultas (`.agents`, `.github`, `.specify`, `.venv`, `.gitignore`), **pero no aparece la carpeta `.git`**. Ejecuta esto en tu terminal para asegurarte de que tu carpeta sigue conectada a GitHub:
   ```bash
   cd ~/proyectos/smc-operaciones
   git status
   ```
   *Si te dice `fatal: not a git repository` (porque se borró o no se había inicializado), reconéctala en 3 segundos con:*
   ```bash
   git init
   git branch -M main
   git remote add origin https://github.com/jalvarez-uv/smc-operaciones.git
   ```

2. **Asegura permisos de ejecución en los scripts de Spec Kit y copia los Excel reales a `data/`:**
   ```bash
   chmod +x .specify/scripts/bash/*.sh
   ```
   Además, copia los 2 archivos Excel que te mandó la empresa (`Control de Operaciones Iquique.xlsx` y `Copia de Proforma de Servicios IQQ 29OCT26 SMC- LBH6526 - SHUN XING 17.xlsx`) dentro de tu carpeta `~/proyectos/smc-operaciones/data/`. Así Antigravity podrá leerlos directamente para hacer las pruebas.

---

## 2. ¿Qué modelo elegir en Antigravity y cuándo hacer Commit?

### Regla de Oro de Commits:
**Sí, haz un commit después de cada comando de Spec Kit.**  
¿Por qué? Porque cada comando de Spec Kit genera artefactos distintos (`constitution.md`, `spec.md`, `plan.md`, `tasks.md` y finalmente el código en `src/`). Si en algún paso el modelo genera algo que no te gusta, tener un commit limpio del paso anterior te permite volver atrás en 1 segundo sin perder nada.

### Selección de Modelos en Antigravity por Etapa:
| Etapa / Comando | Modelo Recomendado en Antigravity | Por qué usar este modelo |
| :--- | :--- | :--- |
| **Paso 1:** `/speckit.constitution` | **Gemini 3.1 Pro (High)** o **Claude Sonnet 4.5 / 4.6 (Thinking)** | Sintetiza reglas arquitectónicas claras y restricciones técnicas sin inventar dependencias innecesarias. |
| **Paso 2:** `/speckit.specify` | **Gemini 3.1 Pro (High)** | Tiene una ventana de contexto excelente para leer tu `docs/SRS.md` completo y transformarlo al formato de especificación de Spec Kit sin perder ningún detalle del negocio marítimo. |
| **Paso 3:** `/speckit.plan` | **Claude Sonnet 4.5 / 4.6 (Thinking)** | Es sobresaliente diseñando arquitectura de software en Python, esquemas SQLite y contratos de módulos desacoplados (`src/core` vs `src/ui`). |
| **Paso 4:** `/speckit.tasks` | **Claude Sonnet 4.5 / 4.6 (Thinking)** | Desglosa el plan técnico en tareas atómicas ordenadas por dependencias y casos de prueba. |
| **Paso 5:** `/speckit.implement` | **Claude Sonnet 4.5 / 4.6** | Es el mejor modelo escribiendo código Python limpio (`openpyxl`, `reportlab`, `customtkinter`), corriendo `pytest` en la terminal y corrigiendo errores por sí solo. |
| **Ajustes rápidos / Consultas** | **Gemini 3 Flash** | Muy rápido para dudas puntuales o retoques menores de interfaz. |

---

## 3. Flujo Paso a Paso con Prompts Exactos y Commits

### 🔹 Paso 0: Primer Commit Base (Documentación y Estructura Inicial)
Antes de pedirle nada al agente en Antigravity, guarda tus archivos `README.md`, `docs/SRS.md` y `docs/PLAN_DE_PRUEBAS.md` y haz tu primer commit en la terminal:

```bash
cd ~/proyectos/smc-operaciones
git add README.md .gitignore requirements.txt docs/ .agents/ .specify/
git commit -m "chore: initialize project structure, SRS, test plan and Spec Kit"
git push -u origin main
```

---

### 🔹 Paso 1: Definir la Constitución del Proyecto (`/speckit.constitution`)
1. Abre **Antigravity** en la carpeta `~/proyectos/smc-operaciones`.
2. Selecciona el modelo **Gemini 3.1 Pro (High)** (o **Claude Sonnet 4.5/4.6 Thinking**).
3. En el chat del agente, escribe exactamente este prompt:

> **Prompt 1:**
> ```text
> /speckit.constitution Establece como principios innegociables del proyecto SMC-Operaciones:
> 1. Arquitectura limpia y modular en Python 3.11+: Toda la lógica de negocio, base de datos SQLite, calculadora de tiempos/tarifas y generación de archivos Excel/PDF debe residir en `src/core/` totalmente desacoplada de la interfaz gráfica en `src/ui/` (CustomTkinter), permitiendo que el módulo pueda usarse tanto como aplicación de escritorio (.exe) como librería integrable al software de la empresa.
> 2. Fidelidad absoluta a los datos y formatos reales de Servicios Marítimos Carrere (SMC): Respetar las 18 columnas de `Control de Operaciones Iquique.xlsx`, los tarifarios únicos por cliente en USD, el formato de Proforma de Servicios y la generación de Órdenes de Compra para lanchas externas como BUCA LAUREL.
> 3. Desarrollo guiado por pruebas (TDD con pytest): Todo cálculo de tiempo (TOTAL TIME incluyendo cruce de medianoche), subtotal USD, recargo EXTRA USD e IVA (19%) debe estar validado con pruebas automatizadas en `tests/` según `docs/PLAN_DE_PRUEBAS.md`.
> 4. Portabilidad Linux/Windows: Usar rutas multiplataforma con `pathlib.Path` y codificación UTF-8 explícita.
> ```

4. **Verifica:** Revisa que se haya actualizado `.specify/memory/constitution.md`.
5. **Haz Commit en tu terminal:**
   ```bash
   git add .specify/memory/constitution.md
   git commit -m "docs(spec): define project constitution and architectural principles"
   git push
   ```

---

### 🔹 Paso 2: Crear la Especificación Funcional (`/speckit.specify`)
1. Mantén **Gemini 3.1 Pro (High)** o **Claude Sonnet 4.5/4.6 (Thinking)**.
2. Pásale este prompt en Antigravity:

> **Prompt 2:**
> ```text
> /speckit.specify Lee íntegramente los archivos `docs/SRS.md` y `docs/PLAN_DE_PRUEBAS.md` y genera la especificación funcional completa del sistema SMC-Operaciones para los 3 apartados solicitados por la empresa:
> 1. Control de Operaciones: Gestión CRUD, filtros por Fecha/Nave/Cliente/Lancha/Estado, cálculo automático de TOTAL TIME (HRS TERMINO - HRS INICIO con soporte de cruce de medianoche) y TOTAL USD (VALOR USD + EXTRA USD), más importación y exportación compatible con `Control de Operaciones Iquique.xlsx`.
> 2. Proforma de Servicios (Orden de Servicio al Cliente): Pre-factura comercial agrupada por Cliente y Nave con tarifario único por cliente (LBH, CPT BOATS, IAN TAYLOR, BUCALEMU, LORENA IQQ), cálculo de Subtotal USD, IVA 19%, Total USD, referencia de Valor Dólar, exportación a Excel (.xlsx) y PDF corporativo, y marcado automático del folio PROFORMA SMC en las operaciones para evitar doble cobro.
> 3. Órdenes de Compra (OC a Proveedores de Lanchas): Liquidación de pagos cuando una lancha externa/arrendada (como BUCA LAUREL) presta servicios a SMC, filtrando dichas maniobras y generando el documento OC en Excel (.xlsx) y PDF.
> ```

3. **Verifica:** El agente ejecutará el script de Spec Kit, creará la rama/carpeta dentro de `specs/` (por ejemplo `specs/001-smc-operaciones/spec.md`) y documentará los escenarios de usuario.
4. **Haz Commit en tu terminal:**
   ```bash
   git add specs/
   git commit -m "docs(spec): generate functional specification for operations, proformas and purchase orders"
   git push
   ```

---

### 🔹 Paso 3: Generar el Plan de Implementación Técnica (`/speckit.plan`)
1. Cambia o mantén el modelo en **Claude Sonnet 4.5 / 4.6 (Thinking)**.
2. Pásale este prompt en Antigravity:

> **Prompt 3:**
> ```text
> /speckit.plan Genera el plan técnico de implementación basado en `docs/SRS.md` utilizando Python 3.11+, SQLite3 (`src/core/database.py`), modelos de dominio (`src/core/models.py`), motor de cálculo y tarifarios (`src/core/calculator.py`), servicio Excel con openpyxl (`src/core/excel_service.py`), servicio PDF con ReportLab (`src/core/pdf_service.py`), e interfaz gráfica moderna en CustomTkinter (`src/ui/app.py`) con pestañas para: 1) Control de Operaciones, 2) Emitir Proforma de Servicios, 3) Emitir Orden de Compra (OC Lanchas), y 4) Tarifarios y Resumen. Incluye el diseño del modelo de datos SQLite y la precarga (seed) de los tarifarios reales de LBH, CPT BOATS, IAN TAYLOR, BUCALEMU y LORENA IQQ, así como las lanchas DOÑA RENATA (propia) y BUCA LAUREL (externa/proveedor).
> ```

3. **Verifica:** Revisa los archivos `plan.md` y `data-model.md` generados dentro de tu carpeta `specs/`.
4. **Haz Commit en tu terminal:**
   ```bash
   git add specs/
   git commit -m "docs(spec): create technical architecture plan and SQLite data model"
   git push
   ```

---

### 🔹 Paso 4: Generar la Lista de Tareas (`/speckit.tasks`)
1. Con **Claude Sonnet 4.5 / 4.6 (Thinking)** seleccionado, envía este prompt:

> **Prompt 4:**
> ```text
> /speckit.tasks Desglosa el plan técnico en tareas secuenciales organizadas en 4 fases claras:
> - Fase 1: Motor Core (`models.py`, `calculator.py`, `database.py` con tarifarios precargados) y pruebas unitarias en `tests/test_calculator.py` cubriendo los casos CP-01 a CP-05 de `docs/PLAN_DE_PRUEBAS.md`.
> - Fase 2: Servicio de Excel (`excel_service.py`) para importar las maniobras de `Control de Operaciones Iquique.xlsx` y exportar Proformas de Servicio y Órdenes de Compra en `.xlsx`, junto con sus pruebas de integración (CP-06 a CP-09).
> - Fase 3: Servicio de PDF (`pdf_service.py`) con ReportLab replicando el diseño oficial de SMC (`Proforma de Servicios IQQ 29OCT26 SMC- LBH6526 - SHUN XING 17.pdf`) y el formato de Orden de Compra a proveedor de lancha.
> - Fase 4: Interfaz gráfica `src/ui/app.py` en CustomTkinter integrando todos los módulos y un punto de entrada `main.py` en la raíz listo para empaquetar con PyInstaller.
> ```

2. **Verifica:** Revisa el archivo `tasks.md` generado en `specs/`.
3. **Haz Commit en tu terminal:**
   ```bash
   git add specs/
   git commit -m "docs(spec): generate phased task breakdown"
   git push
   ```

---

### 🔹 Paso 5: Implementar el Código Fase por Fase (`/speckit.implement`)
**Consejo clave de ingeniería:** No le pidas que implemente las 4 fases de una sola vez. Pídele que implemente **una fase por prompt**, ejecute `pytest` y haces un commit al terminar cada fase:

#### 5.1 Implementar Fase 1 (Motor Core + Base de Datos + Pruebas Unitarias)
- **Modelo:** **Claude Sonnet 4.5 / 4.6**
- **Prompt 5A:**
  ```text
  /speckit.implement Ejecuta únicamente las tareas correspondientes a la Fase 1 (`src/core/models.py`, `src/core/calculator.py`, `src/core/database.py` con los tarifarios y lanchas precargados, y `tests/test_calculator.py`). Al finalizar, ejecuta `pytest -v` en el entorno virtual `.venv` y asegúrate de que todas las pruebas pasen al 100%.
  ```
- **Commit al terminar Fase 1:**
  ```bash
  git add src/ tests/ specs/
  git commit -m "feat(core): implement database, tariff engine, time calculator and unit tests"
  git push
  ```

#### 5.2 Implementar Fase 2 y 3 (Importador/Exportador Excel y Generador PDF)
- **Modelo:** **Claude Sonnet 4.5 / 4.6**
- **Prompt 5B:**
  ```text
  /speckit.implement Ejecuta las tareas de la Fase 2 (`src/core/excel_service.py`) y Fase 3 (`src/core/pdf_service.py`). Asegúrate de que el importador lea correctamente las maniobras del archivo real en `data/Control de Operaciones Iquique.xlsx` ignorando filas vacías finales, y que tanto el exportador Excel como el generador PDF produzcan la Proforma de Servicios (caso SHUN XING 17 con Subtotal 2030.00 USD, IVA 385.70 USD y Total 2415.70 USD) y la Orden de Compra para la lancha externa BUCA LAUREL. Crea y ejecuta los tests en `tests/` con `pytest -v`.
  ```
- **Commit al terminar Fase 2 y 3:**
  ```bash
  git add src/ tests/ specs/
  git commit -m "feat(services): implement Excel importer/exporter and corporate PDF generator for Proformas and OCs"
  git push
  ```

#### 5.3 Implementar Fase 4 (Interfaz Gráfica CustomTkinter)
- **Modelo:** **Claude Sonnet 4.5 / 4.6**
- **Prompt 5C:**
  ```text
  /speckit.implement Ejecuta las tareas de la Fase 4 creando la aplicación de escritorio en `src/ui/app.py` con CustomTkinter (y un archivo `main.py` en la raíz si es necesario). La interfaz debe ser intuitiva, con identidad visual marítima (azul marino y blanco), e incluir:
  1. Pestaña "Control de Operaciones": Tabla con filtros por Cliente, Nave, Lancha y Estado, botón para importar el Excel base, formulario para registrar nuevas maniobras con cálculo automático de TT y tarifa sugerida según Cliente+Servicio.
  2. Pestaña "Emitir Proforma (Clientes)": Selector de Cliente y Nave, vista previa de maniobras a cobrar, ingreso de Folio Proforma y Valor Dólar, cálculo en vivo de Subtotal/IVA/Total USD y botones para exportar a Excel (.xlsx) y PDF (.pdf).
  3. Pestaña "Emitir Orden de Compra (Proveedores Lanchas)": Filtro automático de maniobras realizadas con lanchas externas (ej. BUCA LAUREL), ajuste de costo unitario proveedor, asignación de Folio OC y exportación a Excel y PDF.
  4. Pestaña "Tarifarios y Resumen": Gestión de tarifas por cliente y resumen estadístico de maniobras y facturación en USD.
  Verifica que no existan errores de sintaxis y que todas las pruebas de `pytest` sigan pasando.
  ```
- **Pruébala en tu Linux Mint:**
  ```bash
  source .venv/bin/activate
  python -m src.ui.app
  ```
- **Commit al terminar Fase 4:**
  ```bash
  git add src/ tests/ specs/
  git commit -m "feat(ui): implement CustomTkinter desktop interface for operations, proformas and purchase orders"
  git push
  ```

---

## 4. Paso 6: Cómo funciona la Automatización del `.exe` para Windows en GitHub Actions

1. Guarda el archivo `.github/workflows/build-windows.yml` que te entregué arriba dentro de la carpeta `.github/workflows/` de tu proyecto.
2. Súbelo a GitHub:
   ```bash
   git add .github/workflows/build-windows.yml
   git commit -m "ci(windows): add GitHub Actions workflow to build portable Windows .exe"
   git push origin main
   ```
3. **¿Cómo descargar tu `.exe` compilado para Windows?**
   - Abre en tu navegador `https://github.com/jalvarez-uv/smc-operaciones/actions`.
   - Verás el flujo **"Compilar Ejecutable Windows (.exe)"** ejecutándose en una máquina virtual Windows de GitHub (tarda unos 2 a 3 minutos).
   - Cuando aparezca el check verde ✅, haz clic en la ejecución y abajo en la sección **Artifacts** haz clic en **`SMC_Operaciones_Windows_Portable`**.
   - Se descargará un archivo `.zip` que contiene `SMC_Operaciones.exe` junto con todas sus librerías empaquetadas, listo para funcionar en cualquier computador con Windows 10 u 11 sin necesidad de instalar Python.
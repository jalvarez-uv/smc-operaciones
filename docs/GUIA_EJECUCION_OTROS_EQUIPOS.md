# 💻 Guía para Ejecutar SMC-Operaciones en Otro Dispositivo (Windows o Linux)

Existen **dos formas** de entregar y ejecutar la aplicación en cualquier otro computador de la empresa **Servicios Marítimos Carrere (SMC)**:

---

## Opción 1: Ejecutable Portable en Windows (`.exe`) — *Recomendada para Usuarios Finales*
**Ventaja:** El computador donde se va a usar **NO necesita tener Python instalado** ni configurar nada en consola.

### Pasos para obtener y correr el `.exe`:
1. Entra desde cualquier navegador a tu repositorio:  
   `https://github.com/jalvarez-uv/smc-operaciones/actions`
2. Haz clic en la última ejecución con check verde ✅ del flujo **"Compilar Ejecutable Windows (.exe)"**.
3. Baja hasta la sección **Artifacts** y descarga el archivo **`SMC_Operaciones_Windows_Portable`**.
4. Copia ese archivo `.zip` (por pendrive, Google Drive o correo) al computador con **Windows 10 u 11** de la empresa.
5. **Importante:** Haz clic derecho sobre el `.zip` y selecciona **"Extraer todo..."** (no ejecutes el `.exe` desde adentro del `.zip` sin descomprimirlo).
6. Abre la carpeta extraída y haz doble clic en **`SMC_Operaciones.exe`**.
   - *Nota sobre Windows SmartScreen:* Como es un ejecutable interno sin certificado comercial pagado de Microsoft, la primera vez que se abre en Windows puede aparecer una ventana azul que dice *"Windows protegió su PC"*. Simplemente haz clic en **"Más información"** y luego en **"Ejecutar de todas formas"**.
7. ¡Listo! Al abrirse por primera vez, el programa creará automáticamente su base de datos local en la subcarpeta `data/` y cargará las 476 operaciones históricas de `Control de Operaciones Iquique.xlsx`.

---

## Opción 2: Ejecutar desde el Código Fuente (Windows o Linux) — *Para TI o Integración*
**Ventaja:** Ideal si el área de informática de SMC quiere modificar el código, conectarlo a otro sistema o correrlo en un computador con Python.

### A. En otro computador con Windows (PowerShell o CMD)
1. Instalar **Python 3.11 o superior** desde [python.org](https://www.python.org/downloads/) (marcando la casilla *"Add Python to PATH"* durante la instalación).
2. Descargar o clonar el proyecto y abrir una terminal en la carpeta `smc-operaciones`:
   ```powershell
   git clone https://github.com/jalvarez-uv/smc-operaciones.git
   cd smc-operaciones
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

### B. En otro computador con Linux (Ubuntu / Linux Mint / Debian)
1. Abrir la terminal e instalar `python3-venv` y `python3-tk`:
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-tk git
   ```
2. Clonar el repositorio, crear el entorno virtual y lanzar la app:
   ```bash
   git clone https://github.com/jalvarez-uv/smc-operaciones.git
   cd smc-operaciones
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```

---

## 📂 ¿Dónde se guardan los datos y archivos al mover la app?
- **`data/smc_operaciones.db`**: Es el archivo de base de datos SQLite donde quedan guardadas todas las maniobras, tarifarios, Proformas y Órdenes de Compra. Si quieres respaldar toda la información o llevarla a otro PC, basta con copiar este archivo.
- **`data/export/`**: Aquí se guardan automáticamente todos los archivos `.xlsx` y `.pdf` emitidos por la aplicación.
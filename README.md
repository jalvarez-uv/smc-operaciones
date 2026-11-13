# ⚓ SMC Operaciones — Sistema de Control de Operaciones, Proformas y Órdenes de Compra

Sistema modular desarrollado para **Servicios Marítimos Carrere (SMC)** orientado a la digitalización y automatización de la bitácora de operaciones de lanchas portuarias, liquidación comercial para clientes (**Proformas de Servicio**) y liquidación de pagos a proveedores externos de embarcaciones (**Órdenes de Compra**).

---

## 🎯 Problema que Resuelve
Actualmente, el registro de maniobras portuarias se gestiona manualmente en hojas de cálculo (`Control de Operaciones Iquique.xlsx`), y tanto las **Proformas de Servicio** (pre-facturas por nave/cliente) como las **Órdenes de Compra** (pago a lanchas arrendadas como *BUCA LAUREL*) se confeccionan copiando y pegando datos manualmente entre libros de Excel, generando riesgo de inconsistencias en horarios, tarifas y cruces de datos entre distintas naves.

---

## 🚀 Características Principales (MVP)
- **Control de Operaciones:** Registro, edición, filtrado e importación/exportación de maniobras (`FECHA`, `HRS INICIO`, `HRS TERMINO`, cálculo automático de `TOTAL TIME`, `NAVE`, `CLIENTE`, `SERVICIO`, `TERMINAL`, `LANCHA`, `VALOR USD`, `EXTRA USD`, `TOTAL USD`, `ESTADO`).
- **Motor de Tarifarios por Cliente:** Autocompletado del valor en USD según la matriz `Cliente + Tipo de Servicio` (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`), permitiendo recargos (`EXTRA USD`) y descuentos.
- **Generador Automático de Proformas de Servicio (Excel y PDF):** Selección de maniobras por Cliente y Nave, aplicando tipo de cambio (USD/CLP), cálculo de Subtotal, IVA ($19\%$) y asignación de folio único (`SMC-PDS-IQQ-[CLIENTE]-V[XXXX]`).
- **Generador de Órdenes de Compra (OC Proveedores):** Filtrado automático de operaciones ejecutadas con lanchas externas/arrendadas (ej. `BUCA LAUREL`) para emitir el documento de pago al proveedor de la embarcación.
- **Trazabilidad Comercial:** Vinculación del código de Proforma SMC, OC Cliente y Factura directamente sobre cada maniobra para evitar cobros duplicados.

---

## 🛠️ Stack Tecnológico
- **Lenguaje:** Python 3.11+
- **Persistencia:** SQLite3 + Importación/Exportación nativa `.xlsx` (`openpyxl` / `pandas`)
- **Generación Documental:** `openpyxl` (plantillas Excel con fórmulas) y `ReportLab` (documentos PDF corporativos listos para enviar)
- **Interfaz de Usuario:** `CustomTkinter` (Escritorio multiplataforma Linux/Windows) con arquitectura desacoplada lista para integración
- **Testing:** `pytest`
- **Metodología:** Spec-Driven Development (`spec-kit`) asistido en Antigravity (`agy`)

---

## 📂 Estructura del Proyecto
```text
smc-operaciones/
├── .agents/                    # Workflows de Spec Kit para Antigravity (.agents/workflows/)
├── .github/
│   └── workflows/
│       └── build-windows.yml   # Compilación automática de ejecutable .exe para Windows
├── .specify/                   # Memoria, constitución, scripts y plantillas de Spec Kit
├── data/                       # Base de datos SQLite local y planillas Excel base
├── docs/
│   ├── SRS.md                  # Especificación de Requisitos de Software
│   ├── PLAN_DE_PRUEBAS.md      # Plan de pruebas unitarias, integración y aceptación
│   └── GUIA_ANTIGRAVITY_SPECKIT.md # Guía operativa de desarrollo con Antigravity y Git
├── specs/                      # Especificaciones generadas por Spec Kit
├── src/
│   ├── core/
│   │   ├── database.py         # Conexión SQLite y esquema relacional
│   │   ├── models.py           # Entidades de dominio y validaciones
│   │   ├── calculator.py       # Cálculo de tiempos (TT), tarifas, IVA y conversión USD/CLP
│   │   ├── excel_service.py    # Importador de planilla base y exportador de Proformas/OC
│   │   └── pdf_service.py      # Generador de PDF oficial de Proforma y OC
│   └── ui/
│       └── app.py              # Interfaz gráfica de usuario (CustomTkinter)
├── tests/                      # Suite de pruebas automatizadas con pytest
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Instalación y Ejecución Local

### En Linux Mint / Ubuntu:
```bash
git clone https://github.com/jalvarez-uv/smc-operaciones.git
cd smc-operaciones
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.ui.app
```

### En Windows (Desde Código Fuente):
```powershell
git clone https://github.com/jalvarez-uv/smc-operaciones.git
cd smc-operaciones
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.ui.app
```

### En Windows (Ejecutable Portable `.exe`):
1. Ir a la pestaña **Actions** del repositorio en GitHub.
2. Descargar el artefacto `SMC_Operaciones_Windows_Portable`.
3. Descomprimir el archivo `.zip` y ejecutar `SMC_Operaciones.exe`.

---

## 🧪 Ejecución de Pruebas Automatizadas
```bash
source .venv/bin/activate
pytest -v
```

---

## 👨‍💻 Autor
- **Jorge Eduardo Álvarez Alarcón** — Práctica Profesional para *Servicios Marítimos Carrere (SMC)*.
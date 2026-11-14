"""Punto de entrada principal de SMC-Operaciones (escritorio y empaquetado PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.excel_service import import_operations_from_excel
from src.ui.app import SMCOperacionesApp


def resolve_base_dir() -> Path:
    """Resuelve el directorio base tanto en ejecución normal como en .exe congelado."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bootstrap_application() -> SMCOperacionesApp:
    """Inicializa la base de datos SQLite, precarga la planilla base si está vacía y crea la UI."""
    base_dir = resolve_base_dir()
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "smc_operaciones.db"
    db = DatabaseManager(db_path)
    db.init_db()

    base_excel = data_dir / "Control de Operaciones Iquique.xlsx"
    if not db.list_operaciones() and base_excel.exists():
        operaciones = import_operations_from_excel(base_excel)
        db.bulk_insert_operaciones(operaciones)

    return SMCOperacionesApp(db_manager=db, data_dir=data_dir)


if __name__ == "__main__":
    app = bootstrap_application()
    app.mainloop()


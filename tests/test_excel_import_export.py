"""Pruebas de integración y aceptación para Excel, Base de Datos y PDF (CP-06 a CP-09)."""

from pathlib import Path
import time as time_mod

import openpyxl
import pytest

from src.core.database import DatabaseManager
from src.core.excel_service import (
    export_operations_to_excel,
    generate_orden_compra_excel,
    generate_proforma_excel,
    import_operations_from_excel,
)
from src.core.models import (
    DuplicateProformaError,
    OrdenCompraSummary,
    ProformaSummary,
)
from src.core.pdf_service import (
    generate_orden_compra_pdf,
    generate_proforma_pdf,
)

BASE_EXCEL_PATH = Path("data/Control de Operaciones Iquique.xlsx")


@pytest.fixture
def populated_db() -> DatabaseManager:
    """Base de datos en memoria precargada con las 476 operaciones reales de Iquique."""
    db = DatabaseManager(":memory:")
    db.init_db()
    ops = import_operations_from_excel(BASE_EXCEL_PATH)
    db.bulk_insert_operaciones(ops)
    yield db
    db.close()


def test_cp08_import_476_valid_operations_and_export(tmp_path: Path) -> None:
    """CP-08: Importación íntegra de las 476 operaciones válidas ignorando filas en cero."""
    operaciones = import_operations_from_excel(BASE_EXCEL_PATH)
    assert len(operaciones) == 476

    # Verificar que todas las operaciones tienen nave, cliente y servicio no vacíos
    assert all(op.nave and op.cliente and op.servicio for op in operaciones)

    # Verificar exportación de bitácora a las 18 columnas oficiales
    exported_path = export_operations_to_excel(operaciones[:15], tmp_path / "bitacora_test.xlsx")
    assert exported_path.exists()

    reimported = import_operations_from_excel(exported_path)
    assert len(reimported) == 15
    assert reimported[0].nave == operaciones[0].nave
    assert reimported[0].total_usd == operaciones[0].total_usd


def test_cp06_proforma_shun_xing_17_excel(populated_db: DatabaseManager, tmp_path: Path) -> None:
    """CP-06: Generación de Proforma Real SHUN XING 17 (Subtotal 2030, IVA 385.70, Total 2415.70)."""
    shun_ops = populated_db.list_operaciones(
        fecha_desde="2026-10-29",
        fecha_hasta="2026-10-29",
        cliente="LBH",
        nave="SHUN XING 17",
    )
    assert len(shun_ops) == 5

    cliente = populated_db.get_cliente_by_codigo("LBH")
    assert cliente is not None

    proforma = ProformaSummary(
        folio="SMC-PDS-IQQ-LBH-V6526",
        fecha_emision="2026-10-29",
        cliente=cliente,
        nave_nombre="SHUN XING 17",
        nave_clasificacion="F/V",
        valor_dolar_clp=981.08,
        operaciones=shun_ops,
    )

    out_xlsx = generate_proforma_excel(proforma, tmp_path / "Proforma_SHUN_XING_17.xlsx")
    assert out_xlsx.exists()
    assert proforma.subtotal_usd == 2030.00
    assert proforma.iva_usd == 385.70
    assert proforma.total_usd == 2415.70

    # Inspeccionar el libro Excel generado para asegurar 5 filas exactas y ausencia de otras naves
    wb = openpyxl.load_workbook(out_xlsx, data_only=True)
    ws = wb["PROFORMA DE SERVICIOS"]
    assert ws.cell(row=5, column=6).value == "SMC-PDS-IQQ-LBH-V6526"
    assert ws.cell(row=9, column=4).value == "SHUN XING 17"

    service_rows = []
    for r in range(16, 21):
        srv = ws.cell(row=r, column=1).value
        amt = ws.cell(row=r, column=6).value
        service_rows.append((srv, amt))

    assert len(service_rows) == 5
    assert sum(amt for _, amt in service_rows) == 2030.00
    # Fila 21 debe estar vacía (separador antes del bloque de condiciones en fila 22)
    assert ws.cell(row=21, column=1).value is None
    assert ws.cell(row=22, column=6).value == 2030.00  # Subtotal
    assert ws.cell(row=24, column=6).value == 385.70   # IVA 19%
    assert ws.cell(row=26, column=6).value == 2415.70  # TOTAL
    assert ws.cell(row=27, column=6).value == 2416.0   # TOTAL REDONDEADO
    wb.close()


def test_cp07_orden_compra_buca_laurel(populated_db: DatabaseManager, tmp_path: Path) -> None:
    """CP-07: Generación de Orden de Compra Lancha Externa BUCA LAUREL del 21/10/2026."""
    buca_ops = populated_db.list_operaciones(
        fecha_desde="2026-10-21",
        fecha_hasta="2026-10-21",
        lancha="BUCA LAUREL",
        solo_lancha_externa_pendiente_oc=True,
    )
    assert len(buca_ops) == 6
    naves_incluidas = {op.nave for op in buca_ops}
    assert naves_incluidas == {"RONG HENG 68", "HUA YING 66"}
    assert all(op.lancha == "BUCA LAUREL" for op in buca_ops)

    oc = OrdenCompraSummary(
        folio_oc="SMC-OC-IQQ-BL-V001",
        fecha_emision="2026-10-21",
        proveedor_nombre="Servicios Marítimos Bucalemu / Armador Externo",
        lancha_nombre="BUCA LAUREL",
        operaciones=buca_ops,
    )

    out_xlsx = generate_orden_compra_excel(oc, tmp_path / "OC_BUCA_LAUREL.xlsx")
    assert out_xlsx.exists()
    assert oc.subtotal_usd == 1200.00
    assert oc.iva_usd == 228.00
    assert oc.total_usd == 1428.00

    op_ids = [op.id for op in buca_ops if op.id is not None]
    populated_db.register_orden_compra(oc, op_ids)

    # Verificar que ya no aparecen como pendientes de OC
    pendientes = populated_db.list_operaciones(
        fecha_desde="2026-10-21",
        fecha_hasta="2026-10-21",
        lancha="BUCA LAUREL",
        solo_lancha_externa_pendiente_oc=True,
    )
    assert len(pendientes) == 0


def test_cp09_prevent_double_billing(populated_db: DatabaseManager) -> None:
    """CP-09: Prevención de doble facturación sobre maniobras con folio SMC-PDS-IQQ-LBH-V6526."""
    shun_ops = populated_db.list_operaciones(
        fecha_desde="2026-10-29",
        fecha_hasta="2026-10-29",
        cliente="LBH",
        nave="SHUN XING 17",
    )
    assert len(shun_ops) == 5
    # En la planilla histórica estas 5 maniobras ya traen asignado el folio SMC-PDS-IQQ-LBH-V6526
    assert all(op.proforma_smc == "SMC-PDS-IQQ-LBH-V6526" for op in shun_ops)

    cliente = populated_db.get_cliente_by_codigo("LBH")
    assert cliente is not None

    duplicate_proforma = ProformaSummary(
        folio="SMC-PDS-IQQ-LBH-V9999",
        fecha_emision="2026-11-13",
        cliente=cliente,
        nave_nombre="SHUN XING 17",
        operaciones=shun_ops,
        subtotal_usd=2030.00,
        iva_usd=385.70,
        total_usd=2415.70,
    )

    op_ids = [op.id for op in shun_ops if op.id is not None]
    with pytest.raises(DuplicateProformaError) as exc_info:
        populated_db.register_proforma(duplicate_proforma, op_ids)

    assert "SMC-PDS-IQQ-LBH-V6526" in str(exc_info.value)


def test_pdf_generation_proforma_and_oc(populated_db: DatabaseManager, tmp_path: Path) -> None:
    """Validar generación de PDFs corporativos (<3s, cabecera %PDF-, datos íntegros)."""
    shun_ops = populated_db.list_operaciones(
        fecha_desde="2026-10-29",
        fecha_hasta="2026-10-29",
        cliente="LBH",
        nave="SHUN XING 17",
    )
    cliente = populated_db.get_cliente_by_codigo("LBH")
    assert cliente is not None

    proforma = ProformaSummary(
        folio="SMC-PDS-IQQ-LBH-V6526",
        fecha_emision="2026-10-29",
        cliente=cliente,
        nave_nombre="SHUN XING 17",
        nave_clasificacion="F/V",
        valor_dolar_clp=981.08,
        operaciones=shun_ops,
    )

    t0 = time_mod.perf_counter()
    pdf_proforma_path = generate_proforma_pdf(proforma, tmp_path / "Proforma_SHUN_XING_17.pdf")
    elapsed_proforma = time_mod.perf_counter() - t0

    assert pdf_proforma_path.exists()
    assert elapsed_proforma < 3.0
    raw_proforma = pdf_proforma_path.read_bytes()
    assert raw_proforma.startswith(b"%PDF-")
    assert b"SHUN XING 17" in raw_proforma
    assert b"SMC-PDS-IQQ-LBH-V6526" in raw_proforma
    assert b"77.000.970-7" in raw_proforma
    assert b"2,415.70" in raw_proforma

    buca_ops = populated_db.list_operaciones(
        fecha_desde="2026-10-21",
        fecha_hasta="2026-10-21",
        lancha="BUCA LAUREL",
    )
    oc = OrdenCompraSummary(
        folio_oc="SMC-OC-IQQ-BL-V001",
        fecha_emision="2026-10-21",
        proveedor_nombre="Servicios Marítimos Bucalemu / Armador Externo",
        lancha_nombre="BUCA LAUREL",
        operaciones=buca_ops,
    )

    t1 = time_mod.perf_counter()
    pdf_oc_path = generate_orden_compra_pdf(oc, tmp_path / "OC_BUCA_LAUREL.pdf")
    elapsed_oc = time_mod.perf_counter() - t1

    assert pdf_oc_path.exists()
    assert elapsed_oc < 3.0
    raw_oc = pdf_oc_path.read_bytes()
    assert raw_oc.startswith(b"%PDF-")
    assert b"BUCA LAUREL" in raw_oc
    assert b"RONG HENG 68" in raw_oc
    assert b"HUA YING 66" in raw_oc


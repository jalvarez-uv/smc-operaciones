"""Pruebas unitarias para el motor de cálculo y tarifarios (CP-01 a CP-05)."""

from datetime import time
import pytest

from src.core.calculator import (
    build_proforma_line_description,
    calculate_operation_total_usd,
    calculate_proforma_totals,
    calculate_total_time,
    format_tt_short,
)
from src.core.database import DatabaseManager
from src.core.models import Operacion


@pytest.fixture
def db() -> DatabaseManager:
    manager = DatabaseManager(":memory:")
    manager.init_db()
    yield manager
    manager.close()


def test_cp01_total_time_daytime() -> None:
    """CP-01: Cálculo de TOTAL TIME en horario diurno (09:15:00 a 09:45:00 -> 00:30:00)."""
    assert calculate_total_time("09:15:00", "09:45:00") == "00:30:00"
    assert calculate_total_time(time(9, 15, 0), time(9, 45, 0)) == "00:30:00"


def test_cp02_total_time_midnight_crossover() -> None:
    """CP-02: Cálculo de TOTAL TIME con cruce de medianoche (23:30:00 a 00:45:00 -> 01:15:00)."""
    assert calculate_total_time("23:30:00", "00:45:00") == "01:15:00"
    assert calculate_total_time("23:55", "00:05") == "00:10:00"


def test_total_time_invalid_input() -> None:
    """Validar rechazo de formatos horarios inválidos."""
    with pytest.raises(ValueError):
        calculate_total_time("25:00:00", "01:00:00")
    with pytest.raises(ValueError):
        calculate_total_time("", "01:00:00")


def test_cp03_total_usd_with_extra() -> None:
    """CP-03: Cálculo de TOTAL USD con recargo extra (330.00 + 330.00 -> 660.00)."""
    total = calculate_operation_total_usd(valor_usd=330.00, extra_usd=330.00)
    assert total == 660.00


def test_proforma_totals_iva_19() -> None:
    """Validar cálculo de Subtotal USD, IVA 19% y Total USD (Caso testigo SHUN XING 17)."""
    totals = calculate_proforma_totals(
        line_amounts_usd=[650.0, 350.0, 350.0, 330.0, 350.0],
        valor_dolar_clp=981.08,
    )
    assert totals["subtotal_usd"] == 2030.00
    assert totals["iva_usd"] == 385.70
    assert totals["total_usd"] == 2415.70
    assert totals["total_usd_rounded"] == 2416.0


def test_proforma_line_description_format() -> None:
    """Validar formato exacto de glosa de línea en Proforma SMC."""
    assert format_tt_short("00:35:00") == "0:35:00"
    desc = build_proforma_line_description("2026-10-29", "11:45:00", "12:20:00", "00:35:00")
    assert desc == "29/10/2026        11:45:00    a    12:20:00    TT:    0:35:00"


def test_cp04_tariff_lbh_recepcion(db: DatabaseManager) -> None:
    """CP-04: Autocompletado de Tarifario Cliente LBH + RECEPCIÓN -> 650.00 USD."""
    assert db.get_suggested_tariff("LBH", "RECEPCIÓN") == 650.00
    assert db.get_suggested_tariff("lbh", "recepción") == 650.00


def test_cp05_tariff_cpt_boats_recepcion(db: DatabaseManager) -> None:
    """CP-05: Autocompletado de Tarifario Cliente CPT BOATS + RECEPCIÓN -> 350.00 USD."""
    assert db.get_suggested_tariff("CPT BOATS", "RECEPCIÓN") == 350.00
    assert db.get_suggested_tariff("CPT BOATS", "REGIMEN UP") == 200.00


def test_database_seed_clients_and_boats(db: DatabaseManager) -> None:
    """Verificar precarga de los 5 clientes reales y las 2 lanchas (propia y externa)."""
    clientes = {c.codigo_agencia for c in db.list_clientes()}
    assert clientes == {"LBH", "CPT BOATS", "IAN TAYLOR", "BUCALEMU", "LORENA IQQ"}

    lanchas = {l.nombre: l for l in db.list_lanchas()}
    assert lanchas["DOÑA RENATA"].es_propia is True
    assert lanchas["BUCA LAUREL"].es_propia is False
    assert lanchas["BUCA LAUREL"].tarifa_costo_base_usd == 200.0

    # Verificar idempotencia de seed
    db.seed_initial_data()
    assert len(db.list_clientes()) == 5
    assert len(db.list_tariffs()) == 25


def test_database_crud_and_filters(db: DatabaseManager) -> None:
    """Verificar creación, consulta, filtrado y recálculo automático en SQLite."""
    op_id = db.create_operacion(
        Operacion(
            fecha="2026-10-29",
            hrs_inicio="23:30:00",
            hrs_termino="00:45:00",
            nave="LU PENG YUAN YU 089",
            cliente="LBH",
            servicio="SHIPCHANDLER",
            terminal="GIRA",
            lancha="DOÑA RENATA",
            valor_usd=330.00,
            extra_usd=330.00,
        )
    )
    saved = db.get_operacion(op_id)
    assert saved is not None
    assert saved.total_time == "01:15:00"
    assert saved.total_usd == 660.00
    assert saved.estado == "PENDIENTE"

    filtered = db.list_operaciones(cliente="LBH", nave="LU PENG")
    assert len(filtered) == 1
    assert filtered[0].id == op_id

    db.delete_operacion(op_id)
    assert db.get_operacion(op_id) is None


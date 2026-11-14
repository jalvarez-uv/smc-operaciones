"""Servicio de importación y exportación de archivos Excel (.xlsx) con openpyxl."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Union

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.core.calculator import (
    build_proforma_line_description,
    calculate_operation_total_usd,
    calculate_proforma_totals,
    calculate_total_time,
    normalize_time_str,
)
from src.core.models import Operacion, OrdenCompraSummary, ProformaSummary

OFFICIAL_18_COLUMNS: list[str] = [
    "FECHA ",
    "HRS INICIO",
    "HRS TERMINO",
    "TOTAL TIME",
    "NAVE",
    "CLIENTE",
    "SERVICIO",
    "TERMINAL",
    "LANCHA",
    "VALOR USD",
    "EXTRA USD",
    "TOTAL USD",
    "OBSERVACIONES",
    "ESTADO",
    "PROFORMA SMC",
    "OC CTE",
    "FACTURA SMC",
    "LBH AGENCIAMIENTO",
]

NAVY_FILL = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
ZEBRA_FILL = PatternFill(start_color="F9FAFC", end_color="F9FAFC", fill_type="solid")
WHITE_BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1B365D")
SECTION_FONT = Font(name="Calibri", size=10, bold=True, color="1B365D")
REGULAR_FONT = Font(name="Calibri", size=10, bold=False, color="000000")
BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="000000")

THIN_SIDE = Side(border_style="thin", color="BFBFBF")
THIN_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)


def _normalize_date(value: object) -> str:
    """Convierte datetime, date o string a formato ISO 'YYYY-MM-DD'."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("La fecha de operación está vacía.")
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3:
            dd, mm, yyyy = parts
            if len(yyyy) == 2:
                yyyy = f"20{yyyy}"
            return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"
    return raw[:10]


def _clean_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_float(value: object) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    return float(cleaned) if cleaned else 0.0


def import_operations_from_excel(file_path: Union[Path, str]) -> list[Operacion]:
    """Importa las maniobras válidas desde 'Control de Operaciones Iquique.xlsx'.

    Lee la hoja 'CONTROL OPES' desde la fila 4, mapea las 18 columnas estándar
    y descarta las filas vacías al final que solo contienen fórmulas en cero (CP-08).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo Excel no encontrado: {path}")

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb["CONTROL OPES"] if "CONTROL OPES" in wb.sheetnames else wb.active
        operaciones: list[Operacion] = []

        for row in ws.iter_rows(min_row=4, values_only=True):
            padded = (list(row) + [None] * 18)[:18]
            (
                fecha_val,
                h_ini_val,
                h_fin_val,
                _tt_val,
                nave_val,
                cte_val,
                srv_val,
                term_val,
                lancha_val,
                val_usd_val,
                extra_usd_val,
                _tot_usd_val,
                obs_val,
                est_val,
                prof_val,
                oc_val,
                fac_val,
                lbh_ag_val,
            ) = padded

            nave_str = _clean_str(nave_val)
            cte_str = _clean_str(cte_val)
            srv_str = _clean_str(srv_val)

            # Ignorar filas vacías al final de la hoja que solo tienen fórmulas en cero
            if not nave_str and not cte_str and not srv_str:
                continue

            fecha_str = _normalize_date(fecha_val)
            ini_str = normalize_time_str(h_ini_val)  # type: ignore[arg-type]
            fin_str = normalize_time_str(h_fin_val)  # type: ignore[arg-type]
            tt_str = calculate_total_time(ini_str, fin_str)

            valor_usd = _clean_float(val_usd_val)
            extra_usd = _clean_float(extra_usd_val)
            total_usd = calculate_operation_total_usd(valor_usd, extra_usd)

            estado_str = _clean_str(est_val).upper() or "PENDIENTE"

            operaciones.append(
                Operacion(
                    fecha=fecha_str,
                    hrs_inicio=ini_str,
                    hrs_termino=fin_str,
                    total_time=tt_str,
                    nave=nave_str.upper(),
                    cliente=cte_str.upper(),
                    servicio=srv_str.upper(),
                    terminal=_clean_str(term_val).upper(),
                    lancha=_clean_str(lancha_val).upper(),
                    valor_usd=valor_usd,
                    extra_usd=extra_usd,
                    total_usd=total_usd,
                    observaciones=_clean_str(obs_val),
                    estado=estado_str,
                    proforma_smc=_clean_str(prof_val),
                    oc_cte=_clean_str(oc_val),
                    factura_smc=_clean_str(fac_val),
                    lbh_agenciamiento=_clean_str(lbh_ag_val),
                )
            )

        return operaciones
    finally:
        wb.close()


def _autofit_columns(ws: openpyxl.worksheet.worksheet.Worksheet, max_cols: int = 18) -> None:
    for col_idx in range(1, max_cols + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 10
        for cell in ws[col_letter]:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = min(len(val_str), 48)
        ws.column_dimensions[col_letter].width = max_len + 3


def export_operations_to_excel(
    operaciones: list[Operacion],
    output_path: Union[Path, str],
) -> Path:
    """Exporta la bitácora de operaciones respetando las 18 columnas oficiales de SMC."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CONTROL OPES"

    ws.cell(row=1, column=1, value="PLANILLA CONTROL DE OPERACIONES IQUIQUE ").font = TITLE_FONT
    ws.cell(row=1, column=7, value="SERVICIOS MARITIMOS CARRERE IQQ").font = SECTION_FONT
    ws.cell(row=1, column=13, value="COD: SMC-CRT-OPS-IQQ-V001").font = SECTION_FONT

    for col_idx, header in enumerate(OFFICIAL_18_COLUMNS, start=1):
        cell = ws.cell(row=3, column=col_idx, value=header)
        cell.fill = NAVY_FILL
        cell.font = WHITE_BOLD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    for row_offset, op in enumerate(operaciones, start=4):
        values = [
            op.fecha,
            op.hrs_inicio,
            op.hrs_termino,
            op.total_time or calculate_total_time(op.hrs_inicio, op.hrs_termino),
            op.nave,
            op.cliente,
            op.servicio,
            op.terminal,
            op.lancha,
            float(op.valor_usd),
            float(op.extra_usd),
            float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd)),
            op.observaciones,
            op.estado,
            op.proforma_smc,
            op.oc_cte,
            op.factura_smc,
            op.lbh_agenciamiento,
        ]
        for col_idx, val in enumerate(values, start=1):
            c = ws.cell(row=row_offset, column=col_idx, value=val)
            c.font = REGULAR_FONT
            c.border = THIN_BORDER
            if row_offset % 2 == 1:
                c.fill = ZEBRA_FILL
            if col_idx in (10, 11, 12):
                c.number_format = "$#,##0.00"

    _autofit_columns(ws, max_cols=18)
    wb.save(out)
    return out


def generate_proforma_excel(
    proforma: ProformaSummary,
    output_path: Union[Path, str],
) -> Path:
    """Genera el archivo .xlsx oficial de Proforma de Servicios SMC sin filas residuales (CP-06)."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    line_amounts = [
        float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd))
        for op in proforma.operaciones
    ]
    calc = calculate_proforma_totals(
        line_amounts_usd=line_amounts,
        descuento_usd=proforma.descuento_usd,
        otros_usd=proforma.otros_usd,
        valor_dolar_clp=proforma.valor_dolar_clp,
    )
    proforma.subtotal_usd = calc["subtotal_usd"]
    proforma.iva_usd = calc["iva_usd"]
    proforma.total_usd = calc["total_usd"]
    proforma.total_clp_referencial = calc["total_clp"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PROFORMA DE SERVICIOS"

    # Encabezado Corporativo SMC
    ws.cell(row=1, column=1, value="PROFORMA DE SERVICIOS").font = TITLE_FONT
    ws.cell(row=2, column=1, value="California 5, Cerro Alegre").font = REGULAR_FONT
    ws.cell(row=2, column=3, value="77.000.970-7").font = BOLD_FONT
    ws.cell(row=2, column=5, value="Date").font = BOLD_FONT
    ws.cell(row=2, column=6, value=proforma.fecha_emision).font = REGULAR_FONT

    ws.cell(row=3, column=1, value="Valparaíso, Quinta Región").font = REGULAR_FONT
    ws.cell(row=3, column=5, value="Expiration Date").font = BOLD_FONT
    ws.cell(row=3, column=6, value="-").font = REGULAR_FONT

    ws.cell(row=4, column=1, value="Phone: [+56] 930502169").font = REGULAR_FONT
    ws.cell(row=4, column=5, value="Invoice #").font = BOLD_FONT
    ws.cell(row=4, column=6, value=f"PDS-{proforma.cliente.codigo_agencia}-IQQ").font = REGULAR_FONT

    ws.cell(row=5, column=1, value="Mail: gestion.comercial@servicarre.cl").font = REGULAR_FONT
    ws.cell(row=5, column=5, value="Customer ID").font = BOLD_FONT
    ws.cell(row=5, column=6, value=proforma.folio).font = BOLD_FONT

    ws.cell(row=6, column=1, value="Website: servicarre.cl").font = REGULAR_FONT

    # Bloques CLIENTE | NAVE | DETALLES DEL SERVICIO
    for col_idx, title in [(1, "CLIENTE"), (3, "NAVE"), (5, "DETALLES DEL SERVICIO")]:
        c = ws.cell(row=8, column=col_idx, value=title)
        c.fill = NAVY_FILL
        c.font = WHITE_BOLD_FONT

    ws.cell(row=9, column=1, value="Contacto").font = BOLD_FONT
    ws.cell(row=9, column=2, value=proforma.cliente.contacto_nombre).font = REGULAR_FONT
    ws.cell(row=9, column=3, value="Nombre").font = BOLD_FONT
    ws.cell(row=9, column=4, value=proforma.nave_nombre).font = BOLD_FONT

    ws.cell(row=10, column=1, value="Agencia").font = BOLD_FONT
    ws.cell(row=10, column=2, value=proforma.cliente.codigo_agencia).font = BOLD_FONT
    ws.cell(row=10, column=3, value="Clasificación").font = BOLD_FONT
    ws.cell(row=10, column=4, value=proforma.nave_clasificacion).font = REGULAR_FONT

    ws.cell(row=11, column=1, value="Mail").font = BOLD_FONT
    ws.cell(row=11, column=2, value=proforma.cliente.email).font = REGULAR_FONT
    ws.cell(row=11, column=3, value="Matrícula").font = BOLD_FONT
    ws.cell(row=11, column=4, value="-").font = REGULAR_FONT

    ws.cell(row=12, column=1, value="Phone").font = BOLD_FONT
    ws.cell(row=12, column=2, value=proforma.cliente.telefono).font = REGULAR_FONT
    ws.cell(row=12, column=3, value="Señal de llamada").font = BOLD_FONT
    ws.cell(row=12, column=4, value="-").font = REGULAR_FONT

    ws.cell(row=13, column=3, value="IMO").font = BOLD_FONT
    ws.cell(row=13, column=4, value="-").font = REGULAR_FONT

    unique_services = list(dict.fromkeys(op.servicio for op in proforma.operaciones))
    for idx, srv_name in enumerate(unique_services[:5], start=9):
        ws.cell(row=idx, column=5, value=srv_name).font = REGULAR_FONT

    # Encabezado de tabla de maniobras (Fila 15)
    table_headers = [
        "TIPO SERVICIO",
        "DESCRIPCIÓN",
        "CANTIDAD",
        "PRECIO",
        "Dcto",
        "TOTAL AMOUNT",
    ]
    for col_idx, header in enumerate(table_headers, start=1):
        c = ws.cell(row=15, column=col_idx, value=header)
        c.fill = NAVY_FILL
        c.font = WHITE_BOLD_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = THIN_BORDER

    current_row = 16
    for op in proforma.operaciones:
        tt = op.total_time or calculate_total_time(op.hrs_inicio, op.hrs_termino)
        desc = build_proforma_line_description(op.fecha, op.hrs_inicio, op.hrs_termino, tt)
        line_val = float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd))

        row_values = [
            op.servicio,
            desc,
            1.0,
            line_val,
            0.0,
            line_val,
        ]
        for col_idx, val in enumerate(row_values, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER
            if col_idx in (4, 5, 6):
                cell.number_format = "$#,##0.00"
        current_row += 1

    # Bloque de Condiciones y Totales (sin filas residuales de otras naves)
    summary_start = current_row + 1
    ws.cell(
        row=summary_start,
        column=1,
        value="CONDICIONES DE SERVICIO - OBSERVACIONES",
    ).font = SECTION_FONT
    ws.cell(
        row=summary_start + 1,
        column=1,
        value=f"Valor Dolar {proforma.fecha_emision} ${proforma.valor_dolar_clp:,.2f}",
    ).font = REGULAR_FONT
    ws.cell(
        row=summary_start + 2,
        column=1,
        value="Facturación por total de Proforma.",
    ).font = REGULAR_FONT
    ws.cell(
        row=summary_start + 3,
        column=1,
        value=f"ID: {proforma.folio}",
    ).font = BOLD_FONT

    totals_rows = [
        ("Subtotal", proforma.subtotal_usd, "$#,##0.00"),
        ("IVA %", 0.19, "0%"),
        ("IVA", proforma.iva_usd, "$#,##0.00"),
        ("Otros", proforma.otros_usd, "$#,##0.00"),
        ("TOTAL", proforma.total_usd, "$#,##0.00"),
        ("TOTAL REDONDEADO", calc["total_usd_rounded"], "$#,##0"),
    ]
    for offset, (label, val, num_fmt) in enumerate(totals_rows):
        r_idx = summary_start + offset
        lbl_cell = ws.cell(row=r_idx, column=5, value=label)
        lbl_cell.font = BOLD_FONT
        lbl_cell.fill = SUBHEADER_FILL
        lbl_cell.border = THIN_BORDER

        val_cell = ws.cell(row=r_idx, column=6, value=val)
        val_cell.font = BOLD_FONT if "TOTAL" in label else REGULAR_FONT
        val_cell.number_format = num_fmt
        val_cell.border = THIN_BORDER

    _autofit_columns(ws, max_cols=6)
    wb.save(out)
    return out


def generate_orden_compra_excel(
    oc: OrdenCompraSummary,
    output_path: Union[Path, str],
) -> Path:
    """Genera el archivo .xlsx de Orden de Compra para proveedor de lancha externa (CP-07)."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    line_amounts = [
        float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd))
        for op in oc.operaciones
    ]
    calc = calculate_proforma_totals(line_amounts_usd=line_amounts)
    oc.subtotal_usd = calc["subtotal_usd"]
    oc.iva_usd = calc["iva_usd"]
    oc.total_usd = calc["total_usd"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ORDEN DE COMPRA"

    ws.cell(row=1, column=1, value="ORDEN DE COMPRA - PROVEEDOR DE LANCHA").font = TITLE_FONT
    ws.cell(row=2, column=1, value="Emitido por: Servicios Marítimos Carrere (SMC)").font = BOLD_FONT
    ws.cell(row=2, column=5, value="RUT: 77.000.970-7").font = BOLD_FONT
    ws.cell(row=3, column=1, value="Folio OC:").font = BOLD_FONT
    ws.cell(row=3, column=2, value=oc.folio_oc).font = BOLD_FONT
    ws.cell(row=3, column=5, value="Fecha Emisión:").font = BOLD_FONT
    ws.cell(row=3, column=6, value=oc.fecha_emision).font = REGULAR_FONT

    ws.cell(row=4, column=1, value="Proveedor:").font = BOLD_FONT
    ws.cell(row=4, column=2, value=oc.proveedor_nombre).font = REGULAR_FONT
    ws.cell(row=4, column=5, value="Lancha Arrendada:").font = BOLD_FONT
    ws.cell(row=4, column=6, value=oc.lancha_nombre).font = BOLD_FONT

    headers = [
        "FECHA",
        "HRS INICIO",
        "HRS TERMINO",
        "TOTAL TIME",
        "NAVE ATENDIDA",
        "AGENCIA",
        "SERVICIO",
        "LANCHA",
        "COSTO UNITARIO USD",
        "TOTAL USD",
    ]
    for col_idx, header in enumerate(headers, start=1):
        c = ws.cell(row=6, column=col_idx, value=header)
        c.fill = NAVY_FILL
        c.font = WHITE_BOLD_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = THIN_BORDER

    current_row = 7
    for op in oc.operaciones:
        tt = op.total_time or calculate_total_time(op.hrs_inicio, op.hrs_termino)
        cost_usd = float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd))
        row_vals = [
            op.fecha,
            op.hrs_inicio,
            op.hrs_termino,
            tt,
            op.nave,
            op.cliente,
            op.servicio,
            op.lancha,
            cost_usd,
            cost_usd,
        ]
        for col_idx, val in enumerate(row_vals, start=1):
            c = ws.cell(row=current_row, column=col_idx, value=val)
            c.font = REGULAR_FONT
            c.border = THIN_BORDER
            if col_idx in (9, 10):
                c.number_format = "$#,##0.00"
        current_row += 1

    summary_start = current_row + 1
    if oc.observaciones:
        ws.cell(row=summary_start, column=1, value=f"Observaciones: {oc.observaciones}").font = REGULAR_FONT

    oc_totals = [
        ("Subtotal USD", oc.subtotal_usd),
        ("IVA (19%) USD", oc.iva_usd),
        ("TOTAL OC USD", oc.total_usd),
    ]
    for offset, (label, val) in enumerate(oc_totals):
        r_idx = summary_start + offset
        lbl = ws.cell(row=r_idx, column=9, value=label)
        lbl.font = BOLD_FONT
        lbl.fill = SUBHEADER_FILL
        lbl.border = THIN_BORDER

        vcell = ws.cell(row=r_idx, column=10, value=val)
        vcell.font = BOLD_FONT
        vcell.number_format = "$#,##0.00"
        vcell.border = THIN_BORDER

    _autofit_columns(ws, max_cols=10)
    wb.save(out)
    return out


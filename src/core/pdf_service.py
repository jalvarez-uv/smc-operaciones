"""Servicio de generación de documentos PDF corporativos de SMC con ReportLab."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.core.calculator import (
    build_proforma_line_description,
    calculate_operation_total_usd,
    calculate_proforma_totals,
    calculate_total_time,
)
from src.core.models import OrdenCompraSummary, ProformaSummary

SMC_NAVY = colors.HexColor("#1B365D")
SMC_LIGHT_BG = colors.HexColor("#F2F4F8")
SMC_BORDER = colors.HexColor("#BFBFBF")


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SMCTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=SMC_NAVY,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "SMCSubtitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=SMC_NAVY,
        ),
        "normal": ParagraphStyle(
            "SMCNormal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.black,
        ),
        "bold": ParagraphStyle(
            "SMCBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.black,
        ),
    }


def generate_proforma_pdf(
    proforma: ProformaSummary,
    output_path: Union[Path, str],
) -> Path:
    """Genera el PDF corporativo oficial de Proforma de Servicios SMC (CP-06)."""
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

    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f"Proforma {proforma.folio}",
        author="Servicios Marítimos Carrere (SMC)",
        pageCompression=0,
    )

    story: list[object] = []

    # 1. Encabezado Corporativo SMC
    header_data = [
        [
            Paragraph("<b>PROFORMA DE SERVICIOS</b>", styles["title"]),
            Paragraph(f"<b>Customer ID:</b> {proforma.folio}", styles["bold"]),
        ],
        [
            Paragraph(
                "<b>Servicios Marítimos Carrere (SMC)</b> — RUT: 77.000.970-7<br/>"
                "California 5, Cerro Alegre, Valparaíso / Operaciones Iquique<br/>"
                "Phone: [+56] 930502169 | Mail: gestion.comercial@servicarre.cl | Web: servicarre.cl",
                styles["normal"],
            ),
            Paragraph(
                f"<b>Date:</b> {proforma.fecha_emision}<br/>"
                f"<b>Invoice #:</b> PDS-{proforma.cliente.codigo_agencia}-IQQ<br/>"
                f"<b>Expiration Date:</b> -",
                styles["normal"],
            ),
        ],
    ]
    header_table = Table(header_data, colWidths=[4.8 * inch, 2.7 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 1), (-1, 1), 1.5, SMC_NAVY),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 2. Bloques CLIENTE y NAVE
    client_vessel_data = [
        ["CLIENTE", "", "NAVE ATENDIDA", ""],
        [
            "Agencia:",
            proforma.cliente.codigo_agencia,
            "Nombre Nave:",
            proforma.nave_nombre,
        ],
        [
            "Contacto:",
            proforma.cliente.contacto_nombre,
            "Clasificación:",
            proforma.nave_clasificacion,
        ],
        [
            "Mail:",
            proforma.cliente.email,
            "Puerto / Zona:",
            "IQUIQUE",
        ],
        [
            "Phone:",
            proforma.cliente.telefono,
            "Total Maniobras:",
            str(len(proforma.operaciones)),
        ],
    ]
    cv_table = Table(
        client_vessel_data,
        colWidths=[1.0 * inch, 2.75 * inch, 1.2 * inch, 2.55 * inch],
    )
    cv_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (1, 0), SMC_NAVY),
                ("BACKGROUND", (2, 0), (3, 0), SMC_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, SMC_BORDER),
                ("BACKGROUND", (0, 1), (-1, -1), SMC_LIGHT_BG),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(cv_table)
    story.append(Spacer(1, 12))

    # 3. Tabla de Maniobras
    ops_rows: list[list[object]] = [
        [
            "TIPO SERVICIO",
            "DESCRIPCIÓN",
            "CANTIDAD",
            "PRECIO USD",
            "Dcto",
            "TOTAL AMOUNT",
        ]
    ]
    for op in proforma.operaciones:
        tt = op.total_time or calculate_total_time(op.hrs_inicio, op.hrs_termino)
        desc = build_proforma_line_description(op.fecha, op.hrs_inicio, op.hrs_termino, tt)
        val = float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd))
        ops_rows.append(
            [
                op.servicio,
                desc,
                "1",
                f"${val:,.2f}",
                "$0.00",
                f"${val:,.2f}",
            ]
        )

    ops_table = Table(
        ops_rows,
        colWidths=[1.45 * inch, 3.25 * inch, 0.65 * inch, 0.8 * inch, 0.55 * inch, 0.8 * inch],
    )
    ops_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SMC_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, SMC_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SMC_LIGHT_BG]),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(ops_table)
    story.append(Spacer(1, 12))

    # 4. Bloque de Condiciones y Totales
    summary_data = [
        [
            Paragraph("<b>CONDICIONES DE SERVICIO - OBSERVACIONES</b>", styles["subtitle"]),
            "Subtotal USD",
            f"${proforma.subtotal_usd:,.2f}",
        ],
        [
            Paragraph(
                f"Valor Dolar {proforma.fecha_emision}: ${proforma.valor_dolar_clp:,.2f} CLP",
                styles["normal"],
            ),
            "IVA %",
            "19%",
        ],
        [
            Paragraph("Facturación por total de Proforma.", styles["normal"]),
            "IVA USD",
            f"${proforma.iva_usd:,.2f}",
        ],
        [
            Paragraph(f"<b>ID Folio:</b> {proforma.folio}", styles["bold"]),
            "Otros USD",
            f"${proforma.otros_usd:,.2f}",
        ],
        [
            Paragraph(
                f"Total Referencial CLP: ${proforma.total_clp_referencial:,.0f} CLP "
                f"(Total Redondeado: ${calc['total_usd_rounded']:,.0f} USD)",
                styles["normal"],
            ),
            "TOTAL USD",
            f"${proforma.total_usd:,.2f}",
        ],
    ]
    summary_table = Table(summary_data, colWidths=[4.9 * inch, 1.4 * inch, 1.2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (1, 0), (2, -1), 0.5, SMC_BORDER),
                ("BACKGROUND", (1, 0), (1, -1), SMC_LIGHT_BG),
                ("BACKGROUND", (1, -1), (2, -1), SMC_NAVY),
                ("TEXTCOLOR", (1, -1), (2, -1), colors.white),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, -1), (2, -1), "Helvetica-Bold"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)

    doc.build(story)
    return out


def generate_orden_compra_pdf(
    oc: OrdenCompraSummary,
    output_path: Union[Path, str],
) -> Path:
    """Genera el PDF corporativo de Orden de Compra para proveedor de lancha externa (CP-07)."""
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

    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(out),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f"Orden de Compra {oc.folio_oc}",
        author="Servicios Marítimos Carrere (SMC)",
        pageCompression=0,
    )

    story: list[object] = []

    header_data = [
        [
            Paragraph("<b>ORDEN DE COMPRA — LANCHA EXTERNA</b>", styles["title"]),
            Paragraph(f"<b>Folio OC:</b> {oc.folio_oc}", styles["bold"]),
        ],
        [
            Paragraph(
                "<b>Servicios Marítimos Carrere (SMC)</b> — RUT: 77.000.970-7<br/>"
                f"<b>Proveedor:</b> {oc.proveedor_nombre}<br/>"
                f"<b>Embarcación Arrendada:</b> {oc.lancha_nombre}",
                styles["normal"],
            ),
            Paragraph(
                f"<b>Fecha Emisión:</b> {oc.fecha_emision}<br/>"
                f"<b>Total Maniobras:</b> {len(oc.operaciones)}",
                styles["normal"],
            ),
        ],
    ]
    header_table = Table(header_data, colWidths=[4.8 * inch, 2.7 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 1), (-1, 1), 1.5, SMC_NAVY),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 12))

    table_rows: list[list[object]] = [
        [
            "FECHA",
            "INICIO",
            "TÉRMINO",
            "TT",
            "NAVE ATENDIDA",
            "AGENCIA",
            "SERVICIO",
            "LANCHA",
            "TOTAL USD",
        ]
    ]
    for op in oc.operaciones:
        tt = op.total_time or calculate_total_time(op.hrs_inicio, op.hrs_termino)
        val = float(op.total_usd or calculate_operation_total_usd(op.valor_usd, op.extra_usd))
        table_rows.append(
            [
                op.fecha,
                op.hrs_inicio,
                op.hrs_termino,
                tt,
                op.nave,
                op.cliente,
                op.servicio,
                op.lancha,
                f"${val:,.2f}",
            ]
        )

    ops_table = Table(
        table_rows,
        colWidths=[
            0.78 * inch,
            0.65 * inch,
            0.65 * inch,
            0.62 * inch,
            1.35 * inch,
            0.85 * inch,
            1.0 * inch,
            0.85 * inch,
            0.75 * inch,
        ],
    )
    ops_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SMC_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, SMC_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SMC_LIGHT_BG]),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(ops_table)
    story.append(Spacer(1, 12))

    totals_data = [
        [
            Paragraph(f"Observaciones: {oc.observaciones or 'Liquidación de servicios de lancha externa.'}", styles["normal"]),
            "Subtotal USD",
            f"${oc.subtotal_usd:,.2f}",
        ],
        [
            "",
            "IVA (19%) USD",
            f"${oc.iva_usd:,.2f}",
        ],
        [
            "",
            "TOTAL OC USD",
            f"${oc.total_usd:,.2f}",
        ],
    ]
    totals_table = Table(totals_data, colWidths=[4.9 * inch, 1.4 * inch, 1.2 * inch])
    totals_table.setStyle(
        TableStyle(
            [
                ("GRID", (1, 0), (2, -1), 0.5, SMC_BORDER),
                ("BACKGROUND", (1, 0), (1, -1), SMC_LIGHT_BG),
                ("BACKGROUND", (1, -1), (2, -1), SMC_NAVY),
                ("TEXTCOLOR", (1, -1), (2, -1), colors.white),
                ("FONTNAME", (1, 0), (2, -1), "Helvetica-Bold"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(totals_table)

    doc.build(story)
    return out


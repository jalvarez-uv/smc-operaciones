"""Motor de cálculo de duraciones (TOTAL TIME), tarifas, IVA y glosas de SMC."""

from __future__ import annotations

from datetime import datetime, time
from typing import Union

TimeLike = Union[str, time, datetime]


def normalize_time_str(value: TimeLike) -> str:
    """Normaliza una hora a formato estricto 'HH:MM:SS'.

    Acepta 'HH:MM', 'HH:MM:SS', datetime.time o datetime.datetime.
    Lanza ValueError si el formato o los rangos horarios son inválidos.
    """
    if isinstance(value, datetime):
        return value.strftime("%H:%M:%S")
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if not isinstance(value, str):
        raise ValueError(f"Tipo de hora no soportado: {type(value).__name__}")

    raw = value.strip()
    if not raw:
        raise ValueError("La hora no puede estar vacía.")

    parts = raw.split(":")
    if len(parts) == 2:
        h_str, m_str = parts
        s_str = "00"
    elif len(parts) == 3:
        h_str, m_str, s_str = parts
    else:
        raise ValueError(f"Formato de hora inválido: '{value}'. Use HH:MM o HH:MM:SS.")

    try:
        hours = int(h_str)
        minutes = int(m_str)
        seconds = int(s_str)
    except ValueError as exc:
        raise ValueError(f"Componentes de hora no numéricos en '{value}'.") from exc

    if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59):
        raise ValueError(f"Hora fuera de rango válido (00:00:00 - 23:59:59): '{value}'.")

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _time_str_to_seconds(time_str: str) -> int:
    """Convierte 'HH:MM:SS' a segundos transcurridos desde las 00:00:00."""
    hours, minutes, seconds = (int(p) for p in time_str.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def calculate_total_time(hrs_inicio: TimeLike, hrs_termino: TimeLike) -> str:
    """Calcula la duración efectiva (TT) entre hrs_inicio y hrs_termino en formato 'HH:MM:SS'.

    Si hrs_termino < hrs_inicio (cruce de medianoche, ej. 23:30:00 a 00:45:00),
    suma 24 horas (86400 segundos) automáticamente devolviendo '01:15:00'.
    """
    ini_norm = normalize_time_str(hrs_inicio)
    fin_norm = normalize_time_str(hrs_termino)

    ini_sec = _time_str_to_seconds(ini_norm)
    fin_sec = _time_str_to_seconds(fin_norm)

    if fin_sec < ini_sec:
        fin_sec += 86400

    diff_sec = fin_sec - ini_sec
    hours = diff_sec // 3600
    minutes = (diff_sec % 3600) // 60
    seconds = diff_sec % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_tt_short(total_time: str) -> str:
    """Convierte '00:35:00' al formato corto usado en Proformas SMC: '0:35:00'."""
    norm = normalize_time_str(total_time)
    hours, minutes, seconds = norm.split(":")
    return f"{int(hours)}:{minutes}:{seconds}"


def calculate_operation_total_usd(
    valor_usd: float,
    extra_usd: float = 0.0,
    descuento_usd: float = 0.0,
) -> float:
    """Calcula el monto total en USD de una maniobra: (valor + extra) - descuento."""
    val = float(valor_usd or 0.0)
    extra = float(extra_usd or 0.0)
    desc = float(descuento_usd or 0.0)
    if val < 0:
        raise ValueError("valor_usd no puede ser negativo.")
    total = round((val + extra) - desc, 2)
    if total < 0:
        raise ValueError("El total de la operación en USD no puede ser negativo.")
    return total


def calculate_proforma_totals(
    line_amounts_usd: list[float],
    descuento_usd: float = 0.0,
    otros_usd: float = 0.0,
    iva_rate: float = 0.19,
    valor_dolar_clp: float = 981.08,
) -> dict[str, float]:
    """Calcula Subtotal USD, IVA (19%), Total USD, Total redondeado y Total referencial CLP."""
    subtotal_raw = sum(float(amount) for amount in line_amounts_usd) - float(descuento_usd or 0.0)
    subtotal_usd = round(subtotal_raw, 2)
    iva_usd = round(subtotal_usd * float(iva_rate), 2)
    total_usd = round(subtotal_usd + iva_usd + float(otros_usd or 0.0), 2)
    total_usd_rounded = float(round(total_usd))
    total_clp = float(round(total_usd * float(valor_dolar_clp)))

    return {
        "subtotal_usd": subtotal_usd,
        "iva_usd": iva_usd,
        "total_usd": total_usd,
        "total_usd_rounded": total_usd_rounded,
        "total_clp": total_clp,
    }


def build_proforma_line_description(
    fecha: str,
    hrs_inicio: str,
    hrs_termino: str,
    total_time: str,
) -> str:
    """Construye la glosa oficial de Proforma SMC:

    'DD/MM/YYYY        HH:MM:SS    a    HH:MM:SS    TT:    H:MM:SS'
    """
    fecha_clean = fecha.strip()
    if "-" in fecha_clean and len(fecha_clean) == 10:
        yyyy, mm, dd = fecha_clean.split("-")
        fecha_fmt = f"{dd}/{mm}/{yyyy}"
    else:
        fecha_fmt = fecha_clean

    ini_fmt = normalize_time_str(hrs_inicio)
    fin_fmt = normalize_time_str(hrs_termino)
    tt_short = format_tt_short(total_time)
    return f"{fecha_fmt}        {ini_fmt}    a    {fin_fmt}    TT:    {tt_short}"


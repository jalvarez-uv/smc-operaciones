"""Modelos de dominio y excepciones de negocio para SMC-Operaciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class SMCOperacionesError(Exception):
    """Excepción base del dominio SMC-Operaciones."""


class ValidationError(SMCOperacionesError):
    """Error de validación de datos de dominio."""


class DuplicateProformaError(SMCOperacionesError):
    """Se lanza cuando se intenta asignar una Proforma a maniobras ya facturadas."""

    def __init__(self, message: str, conflicting_folios: Optional[dict[int, str]] = None) -> None:
        super().__init__(message)
        self.conflicting_folios = conflicting_folios or {}


class DuplicateOrdenCompraError(SMCOperacionesError):
    """Se lanza cuando se intenta emitir una Orden de Compra para maniobras ya liquidadas."""

    def __init__(self, message: str, conflicting_folios: Optional[dict[int, str]] = None) -> None:
        super().__init__(message)
        self.conflicting_folios = conflicting_folios or {}


@dataclass
class Cliente:
    """Agencia naviera cliente de Servicios Marítimos Carrere."""

    codigo_agencia: str
    razon_social: str = ""
    contacto_nombre: str = ""
    email: str = ""
    telefono: str = ""
    id: Optional[int] = None


@dataclass
class TarifaCliente:
    """Tarifa base en USD asociada a un cliente y tipo de servicio."""

    cliente_id: int
    codigo_agencia: str
    servicio: str
    valor_usd: float
    id: Optional[int] = None


@dataclass
class ProveedorLancha:
    """Armador o proveedor externo propietario de embarcaciones arrendadas."""

    nombre: str
    rut: str = ""
    contacto: str = ""
    email: str = ""
    id: Optional[int] = None


@dataclass
class Lancha:
    """Embarcación menor que ejecuta las maniobras portuarias."""

    nombre: str
    es_propia: bool = True
    proveedor_nombre: Optional[str] = None
    tarifa_costo_base_usd: float = 0.0
    id: Optional[int] = None


@dataclass
class Operacion:
    """Maniobra portuaria con las 18 columnas oficiales de Control de Operaciones Iquique."""

    fecha: str
    hrs_inicio: str
    hrs_termino: str
    total_time: str = ""
    nave: str = ""
    cliente: str = ""
    servicio: str = ""
    terminal: str = ""
    lancha: str = ""
    valor_usd: float = 0.0
    extra_usd: float = 0.0
    total_usd: float = 0.0
    observaciones: str = ""
    estado: str = "PENDIENTE"
    proforma_smc: str = ""
    oc_cte: str = ""
    factura_smc: str = ""
    lbh_agenciamiento: str = ""
    id: Optional[int] = None
    oc_proveedor_folio: str = ""


@dataclass
class ProformaSummary:
    """Pre-factura comercial (Proforma de Servicios) agrupada por Cliente y Nave."""

    folio: str
    fecha_emision: str
    cliente: Cliente
    nave_nombre: str
    nave_clasificacion: str = "M/N"
    valor_dolar_clp: float = 981.08
    operaciones: list[Operacion] = field(default_factory=list)
    descuento_usd: float = 0.0
    subtotal_usd: float = 0.0
    iva_usd: float = 0.0
    otros_usd: float = 0.0
    total_usd: float = 0.0
    total_clp_referencial: float = 0.0
    observaciones: str = ""


@dataclass
class OrdenCompraSummary:
    """Orden de Compra emitida a proveedor por servicios de lancha externa."""

    folio_oc: str
    fecha_emision: str
    proveedor_nombre: str
    lancha_nombre: str
    operaciones: list[Operacion] = field(default_factory=list)
    subtotal_usd: float = 0.0
    iva_usd: float = 0.0
    total_usd: float = 0.0
    observaciones: str = ""


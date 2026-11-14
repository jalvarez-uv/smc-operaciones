"""Interfaz gráfica moderna tipo Dashboard ERP (2026) en CustomTkinter para SMC-Operaciones."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import customtkinter as ctk

from src.core.calculator import (
    calculate_operation_total_usd,
    calculate_proforma_totals,
    calculate_total_time,
)
from src.core.database import DatabaseManager
from src.core.excel_service import (
    export_operations_to_excel,
    generate_orden_compra_excel,
    generate_proforma_excel,
    import_operations_from_excel,
)
from src.core.models import (
    DuplicateOrdenCompraError,
    DuplicateProformaError,
    Operacion,
    OrdenCompraSummary,
    ProformaSummary,
    ValidationError,
)
from src.core.pdf_service import (
    generate_orden_compra_pdf,
    generate_proforma_pdf,
)

TERMINALES_IQQ = ["GIRA", "SITIO 1", "SITIO 2", "SITIO 3", "SITIO 4", "COMAP", "ESMAX", "COPEC"]
ESTADOS_OP = ["PENDIENTE", "AGENCIA", "FACTURA", "INTERNO"]
SERVICIOS_COMUNES = [
    "RECEPCIÓN",
    "DESPACHO",
    "REGIMEN UP",
    "REGIMEN OUT",
    "SHIPCHANDLER",
    "AMARRA",
    "DESAMARRA",
    "MANIOBRA ABORTADA",
    "RELEVO CONECTORES",
    "RELEVO L/M",
    "EMBARQUE DE ITO VETTING",
]

# Paleta de diseño corporativo moderno (Slate / Maritime Navy / Emerald)
COLOR_SIDEBAR = "#0F172A"
COLOR_SIDEBAR_HOVER = "#1E293B"
COLOR_PRIMARY = "#2563EB"
COLOR_PRIMARY_HOVER = "#1D4ED8"
COLOR_NAVY = "#1B365D"
COLOR_SUCCESS = "#10B981"
COLOR_SUCCESS_HOVER = "#059669"
COLOR_TEAL = "#0D9488"
COLOR_TEAL_HOVER = "#0F766E"
COLOR_DANGER = "#EF4444"
COLOR_DANGER_HOVER = "#DC2626"
COLOR_BG_MAIN = "#F1F5F9"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#E2E8F0"
COLOR_TEXT_MAIN = "#0F172A"
COLOR_TEXT_MUTED = "#64748B"


class SMCOperacionesApp(ctk.CTk):
    """Aplicación de escritorio moderna tipo Dashboard para Servicios Marítimos Carrere (SMC)."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        super().__init__()

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLOR_BG_MAIN)

        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.export_dir = self.data_dir / "export"
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self.db = db_manager or DatabaseManager(self.data_dir / "smc_operaciones.db")
        self.db.init_db()

        self.title("SMC Operaciones — Sistema de Gestión Portuaria, Proformas y Órdenes de Compra")
        self.geometry("1280x720")
        self.minsize(1024, 600)
        self.resizable(True, True)

        self._is_fullscreen = False
        self.bind("<F11>", self._toggle_fullscreen)
        self.after(100, self._maximize_window)

        self._selected_op_id: Optional[int] = None
        self._proforma_ops_map: dict[int, Operacion] = {}
        self._proforma_selected_ids: set[int] = set()
        self._oc_ops_map: dict[int, Operacion] = {}
        self._oc_selected_ids: set[int] = set()

        self._configure_treeview_style()
        self._build_layout()
        self._refresh_all_views()
        self._switch_view("ops")

    # =========================================================================
    # CONFIGURACIÓN VISUAL Y ESTRUCTURA BASE (SIDEBAR + WORKSPACE)
    # =========================================================================
    def _maximize_window(self) -> None:
        """Maximiza la ventana automáticamente tanto en Linux Mint como en Windows."""
        try:
            if sys.platform.startswith("linux"):
                self.attributes("-zoomed", True)
            else:
                self.state("zoomed")
        except Exception:
            pass

    def _toggle_fullscreen(self, _event: object = None) -> None:
        """Alterna modo pantalla completa con F11."""
        self._is_fullscreen = not self._is_fullscreen
        try:
            self.attributes("-fullscreen", self._is_fullscreen)
        except Exception:
            pass

    def _open_export_folder(self) -> None:
        """Abre la carpeta data/export/ en el explorador de archivos del sistema operativo."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path_str = str(self.export_dir.resolve())
        try:
            if sys.platform.startswith("win"):
                os.startfile(path_str)  # type: ignore[attr-defined]
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", path_str])
            else:
                subprocess.Popen(["xdg-open", path_str])
        except Exception as exc:
            messagebox.showinfo("Carpeta de Exportación", f"Archivos guardados en:\n{path_str}\n({exc})")

    def _configure_treeview_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=COLOR_TEXT_MAIN,
            rowheight=28,
            fieldbackground="#FFFFFF",
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=COLOR_NAVY,
            foreground="#FFFFFF",
            relief="flat",
            padding=(6, 6),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", COLOR_PRIMARY)],
            foreground=[("selected", "#FFFFFF")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#25477A")],
        )

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar de navegación izquierdo
        self.sidebar = ctk.CTkFrame(self, width=235, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(18, 14))

        ctk.CTkLabel(
            brand_frame,
            text="⚓ SMC CARRERE",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color="#FFFFFF",
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            brand_frame,
            text="Gestión Portuaria • Iquique",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8",
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color="#1E293B")
        sep.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            self.sidebar,
            text="MÓDULOS PRINCIPALES",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#64748B",
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 6))

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("ops", "📋   Control de Operaciones"),
            ("proforma", "📄   Proformas de Servicio"),
            ("oc", "🚤   Órdenes de Compra (OC)"),
            ("tarifas", "📊   Tarifarios y Dashboard"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=40,
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="transparent",
                text_color="#CBD5E1",
                hover_color=COLOR_SIDEBAR_HOVER,
                command=lambda k=key: self._switch_view(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Acciones rápidas en la parte baja del Sidebar
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", padx=12, pady=14)

        ctk.CTkLabel(
            footer_frame,
            text="ACCESOS RÁPIDOS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#64748B",
            anchor="w",
        ).pack(fill="x", padx=6, pady=(0, 6))

        ctk.CTkButton(
            footer_frame,
            text="📂  Abrir Carpeta Exportados",
            anchor="w",
            height=34,
            corner_radius=6,
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#E2E8F0",
            font=ctk.CTkFont(size=11),
            command=self._open_export_folder,
        ).pack(fill="x", pady=3)

        ctk.CTkButton(
            footer_frame,
            text="📥  Importar Planilla Excel",
            anchor="w",
            height=34,
            corner_radius=6,
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#E2E8F0",
            font=ctk.CTkFont(size=11),
            command=self._import_excel_dialog,
        ).pack(fill="x", pady=3)

        ctk.CTkButton(
            footer_frame,
            text="🖥️  Pantalla Completa (F11)",
            anchor="w",
            height=34,
            corner_radius=6,
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#E2E8F0",
            font=ctk.CTkFont(size=11),
            command=self._toggle_fullscreen,
        ).pack(fill="x", pady=3)

        # 2. Área principal derecha (KPI Strip arriba + Vistas dinámicas abajo)
        self.main_area = ctk.CTkFrame(self, fg_color=COLOR_BG_MAIN, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self._build_kpi_strip()

        self.views_container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.views_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.views_container.grid_rowconfigure(0, weight=1)
        self.views_container.grid_columnconfigure(0, weight=1)

        self.tab_ops = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.tab_proforma = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.tab_oc = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.tab_tarifas = ctk.CTkFrame(self.views_container, fg_color="transparent")

        self.views_map = {
            "ops": self.tab_ops,
            "proforma": self.tab_proforma,
            "oc": self.tab_oc,
            "tarifas": self.tab_tarifas,
        }

        self._build_tab_operaciones()
        self._build_tab_proforma()
        self._build_tab_orden_compra()
        self._build_tab_tarifas_resumen()

    def _build_kpi_strip(self) -> None:
        """Crea la franja superior con 4 tarjetas de indicadores clave (KPIs) en tiempo real."""
        kpi_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        kpi_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))
        for col_idx in range(4):
            kpi_frame.grid_columnconfigure(col_idx, weight=1)

        self.kpi_ops_val = self._create_kpi_card(
            kpi_frame, 0, "MANIOBRAS REGISTRADAS", "0", "Bitácora histórica activa", COLOR_PRIMARY
        )
        self.kpi_usd_val = self._create_kpi_card(
            kpi_frame, 1, "MONTO ACUMULADO (USD)", "$0.00", "Valorización total de servicios", COLOR_SUCCESS
        )
        self.kpi_pending_prof_val = self._create_kpi_card(
            kpi_frame, 2, "SIN PROFORMA ASIGNADA", "0", "Maniobras listas para facturar", "#D97706"
        )
        self.kpi_pending_oc_val = self._create_kpi_card(
            kpi_frame, 3, "LANCHA EXTERNA (PEND. OC)", "0", "Servicios Buca Laurel por liquidar", COLOR_TEAL
        )

    def _create_kpi_card(
        self,
        parent: ctk.CTkFrame,
        col: int,
        title: str,
        initial_value: str,
        subtitle: str,
        accent_color: str,
    ) -> ctk.CTkLabel:
        card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.grid(row=0, column=col, sticky="ew", padx=4)

        top_bar = ctk.CTkFrame(card, height=4, corner_radius=2, fg_color=accent_color)
        top_bar.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=12)

        val_lbl = ctk.CTkLabel(
            card,
            text=initial_value,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        val_lbl.pack(fill="x", padx=12, pady=(1, 1))

        ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=10),
            text_color="#94A3B8",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 6))

        return val_lbl

    def _switch_view(self, view_key: str) -> None:
        """Cambia la vista activa en el área de trabajo y resalta el botón del Sidebar."""
        for key, frame in self.views_map.items():
            frame.grid_forget()
        self.views_map[view_key].grid(row=0, column=0, sticky="nsew")

        for key, btn in self.nav_buttons.items():
            if key == view_key:
                btn.configure(fg_color=COLOR_PRIMARY, text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#CBD5E1")

    def _configure_tree_tags(self, tree: ttk.Treeview) -> None:
        """Aplica colores suaves tipo badge por estado y filas alternadas (zebra)."""
        tree.tag_configure("FACTURA", background="#DCFCE7", foreground="#14532D")
        tree.tag_configure("AGENCIA", background="#DBEAFE", foreground="#1E3A8A")
        tree.tag_configure("PENDIENTE", background="#FEF3C7", foreground="#78350F")
        tree.tag_configure("INTERNO", background="#F1F5F9", foreground="#475569")
        tree.tag_configure("SELECTED_ROW", background="#ECFDF5", foreground="#065F46")
        tree.tag_configure("BILLED_ROW", background="#FFFBEB", foreground="#92400E")
        tree.tag_configure("EVEN", background="#FFFFFF")
        tree.tag_configure("ODD", background="#F8FAFC")

    # =========================================================================
    # PESTAÑA 1: CONTROL DE OPERACIONES (DISEÑO MODERNO EN TARJETAS)
    # =========================================================================
    def _build_tab_operaciones(self) -> None:
        # 1. Tarjeta de Búsqueda Instantánea y Filtros
        filter_card = ctk.CTkFrame(
            self.tab_ops, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        filter_card.pack(fill="x", side="top", pady=(0, 6))

        f_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            f_inner, text="🔍 Buscar Nave:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MAIN
        ).grid(row=0, column=0, padx=4, pady=3)
        self.flt_nave = ctk.CTkEntry(f_inner, width=150, height=28, placeholder_text="Ej. SHUN XING...")
        self.flt_nave.grid(row=0, column=1, padx=4, pady=3)
        self.flt_nave.bind("<KeyRelease>", lambda _e: self._load_operations_table())

        ctk.CTkLabel(f_inner, text="Desde:", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=3, pady=3)
        self.flt_desde = ctk.CTkEntry(f_inner, width=92, height=28, placeholder_text="YYYY-MM-DD")
        self.flt_desde.grid(row=0, column=3, padx=3, pady=3)

        ctk.CTkLabel(f_inner, text="Hasta:", font=ctk.CTkFont(size=11)).grid(row=0, column=4, padx=3, pady=3)
        self.flt_hasta = ctk.CTkEntry(f_inner, width=92, height=28, placeholder_text="YYYY-MM-DD")
        self.flt_hasta.grid(row=0, column=5, padx=3, pady=3)

        ctk.CTkLabel(f_inner, text="Cliente:", font=ctk.CTkFont(size=11)).grid(row=0, column=6, padx=3, pady=3)
        self.flt_cliente = ctk.CTkComboBox(
            f_inner, width=115, height=28, values=["TODOS"], command=lambda _v: self._load_operations_table()
        )
        self.flt_cliente.set("TODOS")
        self.flt_cliente.grid(row=0, column=7, padx=3, pady=3)

        ctk.CTkLabel(f_inner, text="Lancha:", font=ctk.CTkFont(size=11)).grid(row=0, column=8, padx=3, pady=3)
        self.flt_lancha = ctk.CTkComboBox(
            f_inner, width=125, height=28, values=["TODAS"], command=lambda _v: self._load_operations_table()
        )
        self.flt_lancha.set("TODAS")
        self.flt_lancha.grid(row=0, column=9, padx=3, pady=3)

        ctk.CTkLabel(f_inner, text="Estado:", font=ctk.CTkFont(size=11)).grid(row=0, column=10, padx=3, pady=3)
        self.flt_estado = ctk.CTkComboBox(
            f_inner,
            width=105,
            height=28,
            values=["TODOS", *ESTADOS_OP],
            command=lambda _v: self._load_operations_table(),
        )
        self.flt_estado.set("TODOS")
        self.flt_estado.grid(row=0, column=11, padx=3, pady=3)

        ctk.CTkButton(
            f_inner,
            text="Filtrar",
            width=70,
            height=28,
            fg_color=COLOR_PRIMARY,
            command=self._load_operations_table,
        ).grid(row=0, column=12, padx=4, pady=3)

        ctk.CTkButton(
            f_inner,
            text="Restablecer",
            width=82,
            height=28,
            fg_color="#64748B",
            hover_color="#475569",
            command=self._clear_filters,
        ).grid(row=0, column=13, padx=3, pady=3)

        # 2. Tarjeta de Registro y Edición Rápida (Empaquetada arriba de la tabla de forma limpia)
        form_card = ctk.CTkFrame(
            self.tab_ops, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        form_card.pack(fill="x", side="top", pady=(0, 6))

        form_header = ctk.CTkFrame(form_card, fg_color="#F8FAFC", corner_radius=8, height=32)
        form_header.pack(fill="x", padx=6, pady=(6, 4))

        self.form_mode_lbl = ctk.CTkLabel(
            form_header,
            text="✏️  Formulario de Maniobra (Modo: Nueva Operación — Haz clic en una fila abajo para editar)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_NAVY,
        )
        self.form_mode_lbl.pack(side="left", padx=10, pady=4)

        # Leyenda de colores de estado
        legend_frame = ctk.CTkFrame(form_header, fg_color="transparent")
        legend_frame.pack(side="right", padx=8)
        for text, bg_col, txt_col in [
            ("FACTURA", "#DCFCE7", "#14532D"),
            ("AGENCIA", "#DBEAFE", "#1E3A8A"),
            ("PENDIENTE", "#FEF3C7", "#78350F"),
        ]:
            lbl = ctk.CTkLabel(
                legend_frame,
                text=f" {text} ",
                fg_color=bg_col,
                text_color=txt_col,
                corner_radius=4,
                font=ctk.CTkFont(size=9, weight="bold"),
            )
            lbl.pack(side="left", padx=3, pady=2)

        form_grid = ctk.CTkFrame(form_card, fg_color="transparent")
        form_grid.pack(fill="x", padx=8, pady=2)

        # Fila 0: Datos Operativos y Horario
        self.op_fecha = self._labeled_entry(form_grid, "Fecha:", 0, 0, width=95)
        self.op_fecha.insert(0, date.today().isoformat())

        self.op_inicio = self._labeled_entry(form_grid, "Inicio:", 0, 2, width=78)
        self.op_inicio.insert(0, "08:00:00")
        self.op_inicio.bind("<KeyRelease>", lambda _e: self._recalculate_form_values())
        self.op_inicio.bind("<FocusOut>", lambda _e: self._recalculate_form_values())

        self.op_termino = self._labeled_entry(form_grid, "Término:", 0, 4, width=78)
        self.op_termino.insert(0, "09:00:00")
        self.op_termino.bind("<KeyRelease>", lambda _e: self._recalculate_form_values())
        self.op_termino.bind("<FocusOut>", lambda _e: self._recalculate_form_values())

        self.op_tt = self._labeled_entry(form_grid, "⏱️ TT:", 0, 6, width=78)
        self.op_tt.insert(0, "01:00:00")

        self.op_nave = self._labeled_entry(form_grid, "Nave:", 0, 8, width=145)

        ctk.CTkLabel(form_grid, text="Cliente:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=10, padx=3, pady=3, sticky="e"
        )
        self.op_cliente = ctk.CTkComboBox(
            form_grid,
            width=115,
            height=28,
            values=["LBH"],
            command=lambda _v: self._autofill_tariff(),
        )
        self.op_cliente.grid(row=0, column=11, padx=3, pady=3)

        # Fila 1: Servicio, Lancha y Valorización Automática USD
        ctk.CTkLabel(form_grid, text="Servicio:", font=ctk.CTkFont(size=11)).grid(
            row=1, column=0, padx=3, pady=3, sticky="e"
        )
        self.op_servicio = ctk.CTkComboBox(
            form_grid,
            width=150,
            height=28,
            values=SERVICIOS_COMUNES,
            command=lambda _v: self._autofill_tariff(),
        )
        self.op_servicio.grid(row=1, column=1, padx=3, pady=3)

        ctk.CTkLabel(form_grid, text="Terminal:", font=ctk.CTkFont(size=11)).grid(
            row=1, column=2, padx=3, pady=3, sticky="e"
        )
        self.op_terminal = ctk.CTkComboBox(form_grid, width=95, height=28, values=TERMINALES_IQQ)
        self.op_terminal.set("GIRA")
        self.op_terminal.grid(row=1, column=3, padx=3, pady=3)

        ctk.CTkLabel(form_grid, text="Lancha:", font=ctk.CTkFont(size=11)).grid(
            row=1, column=4, padx=3, pady=3, sticky="e"
        )
        self.op_lancha = ctk.CTkComboBox(form_grid, width=125, height=28, values=["DOÑA RENATA", "BUCA LAUREL"])
        self.op_lancha.set("DOÑA RENATA")
        self.op_lancha.grid(row=1, column=5, padx=3, pady=3)

        self.op_valor = self._labeled_entry(form_grid, "Valor USD:", 1, 6, width=78)
        self.op_valor.insert(0, "0.00")
        self.op_valor.bind("<KeyRelease>", lambda _e: self._recalculate_form_values())

        self.op_extra = self._labeled_entry(form_grid, "Extra USD:", 1, 8, width=78)
        self.op_extra.insert(0, "0.00")
        self.op_extra.bind("<KeyRelease>", lambda _e: self._recalculate_form_values())

        self.op_total = self._labeled_entry(form_grid, "💵 Total USD:", 1, 10, width=85)
        self.op_total.insert(0, "0.00")

        # Fila 2: Trazabilidad Comercial
        ctk.CTkLabel(form_grid, text="Estado:", font=ctk.CTkFont(size=11)).grid(
            row=2, column=0, padx=3, pady=3, sticky="e"
        )
        self.op_estado = ctk.CTkComboBox(form_grid, width=110, height=28, values=ESTADOS_OP)
        self.op_estado.set("PENDIENTE")
        self.op_estado.grid(row=2, column=1, padx=3, pady=3)

        self.op_obs = self._labeled_entry(form_grid, "Observaciones:", 2, 2, width=135)
        self.op_proforma = self._labeled_entry(form_grid, "Proforma SMC:", 2, 4, width=135)
        self.op_oc_cte = self._labeled_entry(form_grid, "OC Cliente:", 2, 6, width=85)
        self.op_factura = self._labeled_entry(form_grid, "Factura SMC:", 2, 8, width=85)
        self.op_lbh_ag = self._labeled_entry(form_grid, "LBH Agenc.:", 2, 10, width=85)

        # Barra de Botones de Acción
        action_bar = ctk.CTkFrame(form_card, fg_color="transparent")
        action_bar.pack(fill="x", padx=10, pady=(4, 8))

        ctk.CTkButton(
            action_bar,
            text="➕ Guardar Nueva Maniobra",
            width=175,
            height=32,
            corner_radius=6,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_new_op,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            action_bar,
            text="💾 Actualizar Seleccionada",
            width=175,
            height=32,
            corner_radius=6,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._update_selected_op,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            action_bar,
            text="🗑️ Eliminar",
            width=100,
            height=32,
            corner_radius=6,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            command=self._delete_selected_op,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            action_bar,
            text="🧹 Limpiar Formulario",
            width=140,
            height=32,
            corner_radius=6,
            fg_color="#64748B",
            hover_color="#475569",
            command=self._reset_op_form,
        ).pack(side="left", padx=4)

        self.ops_count_lbl = ctk.CTkLabel(
            action_bar,
            text="Mostrando 0 maniobras",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
        )
        self.ops_count_lbl.pack(side="left", padx=14)

        ctk.CTkButton(
            action_bar,
            text="📤 Exportar Vista a Excel",
            width=170,
            height=32,
            corner_radius=6,
            fg_color=COLOR_NAVY,
            command=self._export_current_view,
        ).pack(side="right", padx=4)

        # 3. Tabla de 18 Columnas con Etiquetas de Color por Estado
        table_card = ctk.CTkFrame(
            self.tab_ops, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        table_card.pack(fill="both", expand=True)

        cols = (
            "id",
            "fecha",
            "hrs_inicio",
            "hrs_termino",
            "total_time",
            "nave",
            "cliente",
            "servicio",
            "terminal",
            "lancha",
            "valor_usd",
            "extra_usd",
            "total_usd",
            "observaciones",
            "estado",
            "proforma_smc",
            "oc_cte",
            "factura_smc",
            "lbh_agenciamiento",
        )
        self.ops_tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse", height=12)
        self._configure_tree_tags(self.ops_tree)

        headers_map = {
            "id": ("ID", 45),
            "fecha": ("FECHA", 88),
            "hrs_inicio": ("HRS INICIO", 80),
            "hrs_termino": ("HRS TERMINO", 85),
            "total_time": ("TOTAL TIME", 80),
            "nave": ("NAVE", 145),
            "cliente": ("CLIENTE", 95),
            "servicio": ("SERVICIO", 130),
            "terminal": ("TERMINAL", 82),
            "lancha": ("LANCHA", 110),
            "valor_usd": ("VALOR USD", 82),
            "extra_usd": ("EXTRA USD", 82),
            "total_usd": ("TOTAL USD", 85),
            "observaciones": ("OBSERVACIONES", 130),
            "estado": ("ESTADO", 85),
            "proforma_smc": ("PROFORMA SMC", 160),
            "oc_cte": ("OC CTE", 85),
            "factura_smc": ("FACTURA SMC", 92),
            "lbh_agenciamiento": ("LBH AGENC.", 100),
        }
        for col_id, (title, width) in headers_map.items():
            self.ops_tree.heading(col_id, text=title)
            self.ops_tree.column(col_id, width=width, minwidth=45)

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.ops_tree.yview)
        hsb = ttk.Scrollbar(table_card, orient="horizontal", command=self.ops_tree.xview)
        self.ops_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.ops_tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=(6, 0))
        hsb.grid(row=1, column=0, sticky="ew", padx=(6, 0), pady=(0, 6))
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        self.ops_tree.bind("<<TreeviewSelect>>", self._on_op_select)

    def _labeled_entry(
        self, parent: ctk.CTkFrame, label: str, row: int, col: int, width: int = 110
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11)).grid(
            row=row, column=col, padx=3, pady=3, sticky="e"
        )
        entry = ctk.CTkEntry(parent, width=width, height=28)
        entry.grid(row=row, column=col + 1, padx=3, pady=3, sticky="w")
        return entry

    def _autofill_tariff(self) -> None:
        cliente = self.op_cliente.get().strip()
        servicio = self.op_servicio.get().strip()
        suggested = self.db.get_suggested_tariff(cliente, servicio)
        if suggested is not None:
            self.op_valor.delete(0, "end")
            self.op_valor.insert(0, f"{suggested:.2f}")
            self._recalculate_form_values()

    def _recalculate_form_values(self) -> None:
        try:
            tt = calculate_total_time(self.op_inicio.get(), self.op_termino.get())
            self.op_tt.delete(0, "end")
            self.op_tt.insert(0, tt)
        except ValueError:
            pass

        try:
            val = float(self.op_valor.get() or 0.0)
            extra = float(self.op_extra.get() or 0.0)
            tot = calculate_operation_total_usd(val, extra)
            self.op_total.delete(0, "end")
            self.op_total.insert(0, f"{tot:.2f}")
        except ValueError:
            pass

    def _build_op_from_form(self) -> Operacion:
        return Operacion(
            id=self._selected_op_id,
            fecha=self.op_fecha.get().strip(),
            hrs_inicio=self.op_inicio.get().strip(),
            hrs_termino=self.op_termino.get().strip(),
            nave=self.op_nave.get().strip(),
            cliente=self.op_cliente.get().strip(),
            servicio=self.op_servicio.get().strip(),
            terminal=self.op_terminal.get().strip(),
            lancha=self.op_lancha.get().strip(),
            valor_usd=float(self.op_valor.get() or 0.0),
            extra_usd=float(self.op_extra.get() or 0.0),
            observaciones=self.op_obs.get().strip(),
            estado=self.op_estado.get().strip(),
            proforma_smc=self.op_proforma.get().strip(),
            oc_cte=self.op_oc_cte.get().strip(),
            factura_smc=self.op_factura.get().strip(),
            lbh_agenciamiento=self.op_lbh_ag.get().strip(),
        )

    def _save_new_op(self) -> None:
        try:
            op = self._build_op_from_form()
            if not op.nave or not op.cliente or not op.servicio:
                messagebox.showwarning("Validación", "Nave, Cliente y Servicio son obligatorios.")
                return
            self.db.create_operacion(op)
            self._reset_op_form()
            self._refresh_all_views()
            messagebox.showinfo("Operación Registrada", "La maniobra fue guardada exitosamente.")
        except Exception as exc:
            messagebox.showerror("Error al Guardar", str(exc))

    def _update_selected_op(self) -> None:
        if self._selected_op_id is None:
            messagebox.showwarning("Selección", "Seleccione una operación de la tabla primero.")
            return
        try:
            op = self._build_op_from_form()
            self.db.update_operacion(self._selected_op_id, op)
            self._refresh_all_views()
            messagebox.showinfo("Actualizado", f"Maniobra ID #{self._selected_op_id} actualizada correctamente.")
        except Exception as exc:
            messagebox.showerror("Error al Actualizar", str(exc))

    def _delete_selected_op(self) -> None:
        if self._selected_op_id is None:
            messagebox.showwarning("Selección", "Seleccione una operación de la tabla primero.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar maniobra ID #{self._selected_op_id}?"):
            self.db.delete_operacion(self._selected_op_id)
            self._reset_op_form()
            self._refresh_all_views()

    def _reset_op_form(self) -> None:
        self._selected_op_id = None
        self.form_mode_lbl.configure(
            text="✏️  Formulario de Maniobra (Modo: Nueva Operación — Haz clic en una fila abajo para editar)"
        )
        self.op_nave.delete(0, "end")
        self.op_valor.delete(0, "end")
        self.op_valor.insert(0, "0.00")
        self.op_extra.delete(0, "end")
        self.op_extra.insert(0, "0.00")
        self.op_total.delete(0, "end")
        self.op_total.insert(0, "0.00")
        self.op_obs.delete(0, "end")
        self.op_proforma.delete(0, "end")
        self.op_oc_cte.delete(0, "end")
        self.op_factura.delete(0, "end")
        self.op_lbh_ag.delete(0, "end")
        self.op_estado.set("PENDIENTE")

    def _on_op_select(self, _event: object) -> None:
        sel = self.ops_tree.selection()
        if not sel:
            return
        vals = self.ops_tree.item(sel[0], "values")
        if not vals:
            return
        op_id = int(vals[0])
        op = self.db.get_operacion(op_id)
        if not op:
            return
        self._selected_op_id = op.id
        self.form_mode_lbl.configure(
            text=f"✏️  Editando Maniobra ID #{op.id} — Nave: {op.nave} ({op.fecha})"
        )

        for widget, val in [
            (self.op_fecha, op.fecha),
            (self.op_inicio, op.hrs_inicio),
            (self.op_termino, op.hrs_termino),
            (self.op_tt, op.total_time),
            (self.op_nave, op.nave),
            (self.op_valor, f"{op.valor_usd:.2f}"),
            (self.op_extra, f"{op.extra_usd:.2f}"),
            (self.op_total, f"{op.total_usd:.2f}"),
            (self.op_obs, op.observaciones),
            (self.op_proforma, op.proforma_smc),
            (self.op_oc_cte, op.oc_cte),
            (self.op_factura, op.factura_smc),
            (self.op_lbh_ag, op.lbh_agenciamiento),
        ]:
            widget.delete(0, "end")
            widget.insert(0, val)

        self.op_cliente.set(op.cliente)
        self.op_servicio.set(op.servicio)
        self.op_terminal.set(op.terminal)
        self.op_lancha.set(op.lancha)
        self.op_estado.set(op.estado)

    def _get_filtered_ops(self) -> list[Operacion]:
        cliente = self.flt_cliente.get()
        lancha = self.flt_lancha.get()
        estado = self.flt_estado.get()
        return self.db.list_operaciones(
            fecha_desde=self.flt_desde.get().strip() or None,
            fecha_hasta=self.flt_hasta.get().strip() or None,
            nave=self.flt_nave.get().strip() or None,
            cliente=None if cliente in ("", "TODOS") else cliente,
            lancha=None if lancha in ("", "TODAS") else lancha,
            estado=None if estado in ("", "TODOS") else estado,
        )

    def _load_operations_table(self) -> None:
        self.ops_tree.delete(*self.ops_tree.get_children())
        ops = self._get_filtered_ops()
        total_vista = sum(o.total_usd for o in ops)
        self.ops_count_lbl.configure(
            text=f"Mostrando {len(ops)} maniobras  •  Suma vista: ${total_vista:,.2f} USD"
        )

        for idx, op in enumerate(ops):
            estado_tag = op.estado.upper() if op.estado.upper() in ESTADOS_OP else ("EVEN" if idx % 2 == 0 else "ODD")
            self.ops_tree.insert(
                "",
                "end",
                tags=(estado_tag,),
                values=(
                    op.id,
                    op.fecha,
                    op.hrs_inicio,
                    op.hrs_termino,
                    op.total_time,
                    op.nave,
                    op.cliente,
                    op.servicio,
                    op.terminal,
                    op.lancha,
                    f"${op.valor_usd:,.2f}",
                    f"${op.extra_usd:,.2f}",
                    f"${op.total_usd:,.2f}",
                    op.observaciones,
                    op.estado,
                    op.proforma_smc,
                    op.oc_cte,
                    op.factura_smc,
                    op.lbh_agenciamiento,
                ),
            )

    def _clear_filters(self) -> None:
        self.flt_desde.delete(0, "end")
        self.flt_hasta.delete(0, "end")
        self.flt_nave.delete(0, "end")
        self.flt_cliente.set("TODOS")
        self.flt_lancha.set("TODAS")
        self.flt_estado.set("TODOS")
        self._load_operations_table()

    def _import_excel_dialog(self) -> None:
        default_xlsx = self.data_dir / "Control de Operaciones Iquique.xlsx"
        file_str = filedialog.askopenfilename(
            title="Seleccionar Planilla Control de Operaciones (.xlsx)",
            initialdir=str(self.data_dir),
            initialfile=default_xlsx.name if default_xlsx.exists() else "",
            filetypes=[("Archivos Excel", "*.xlsx")],
        )
        if not file_str:
            return
        try:
            ops = import_operations_from_excel(Path(file_str))
            replace = messagebox.askyesno(
                "Modo de Importación",
                f"Se encontraron {len(ops)} maniobras válidas.\n¿Desea reemplazar los registros actuales?",
            )
            count = self.db.bulk_insert_operaciones(ops, clear_existing=replace)
            self._refresh_all_views()
            messagebox.showinfo("Importación Exitosa", f"Se importaron {count} maniobras correctamente.")
        except Exception as exc:
            messagebox.showerror("Error de Importación", str(exc))

    def _export_current_view(self) -> None:
        ops = self._get_filtered_ops()
        out_str = filedialog.asksaveasfilename(
            title="Guardar Bitácora en Excel",
            initialdir=str(self.export_dir),
            initialfile=f"Control_Operaciones_Export_{date.today().isoformat()}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Archivos Excel", "*.xlsx")],
        )
        if not out_str:
            return
        try:
            path = export_operations_to_excel(ops, Path(out_str))
            messagebox.showinfo("Exportación Exitosa", f"Bitácora exportada a:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error al Exportar", str(exc))

    # =========================================================================
    # PESTAÑA 2: EMITIR PROFORMA DE SERVICIOS (GUIADA POR PASOS)
    # =========================================================================
    def _build_tab_proforma(self) -> None:
        # Paso 1: Barra superior de selección de Cliente y Nave
        top_card = ctk.CTkFrame(
            self.tab_proforma, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        top_card.pack(fill="x", side="top", pady=(0, 6))

        top_bar = ctk.CTkFrame(top_card, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            top_bar,
            text="PASO 1 • Cliente y Nave:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_NAVY,
        ).grid(row=0, column=0, padx=(4, 8), pady=4)

        ctk.CTkLabel(top_bar, text="Agencia:").grid(row=0, column=1, padx=3, pady=4)
        self.prof_cliente = ctk.CTkComboBox(
            top_bar,
            width=125,
            height=30,
            values=["LBH"],
            command=lambda _v: self._on_proforma_client_change(),
        )
        self.prof_cliente.grid(row=0, column=2, padx=4, pady=4)

        ctk.CTkLabel(top_bar, text="Nave Atendida:").grid(row=0, column=3, padx=3, pady=4)
        self.prof_nave = ctk.CTkComboBox(
            top_bar,
            width=215,
            height=30,
            values=[""],
            command=lambda _v: self._search_proforma_ops(),
        )
        self.prof_nave.grid(row=0, column=4, padx=4, pady=4)

        ctk.CTkLabel(top_bar, text="Desde:").grid(row=0, column=5, padx=3, pady=4)
        self.prof_desde = ctk.CTkEntry(top_bar, width=95, height=30, placeholder_text="YYYY-MM-DD")
        self.prof_desde.grid(row=0, column=6, padx=3, pady=4)

        ctk.CTkLabel(top_bar, text="Hasta:").grid(row=0, column=7, padx=3, pady=4)
        self.prof_hasta = ctk.CTkEntry(top_bar, width=95, height=30, placeholder_text="YYYY-MM-DD")
        self.prof_hasta.grid(row=0, column=8, padx=3, pady=4)

        ctk.CTkButton(
            top_bar, text="🔍 Buscar", width=90, height=30, fg_color=COLOR_PRIMARY, command=self._search_proforma_ops
        ).grid(row=0, column=9, padx=4, pady=4)

        ctk.CTkButton(
            top_bar,
            text="☑️ Marcar Todas",
            width=110,
            height=30,
            fg_color="#475569",
            command=self._select_all_proforma,
        ).grid(row=0, column=10, padx=4, pady=4)

        ctk.CTkButton(
            top_bar,
            text="🚀 Emitir Proforma (Excel + PDF)",
            width=215,
            height=32,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._emit_proforma,
        ).grid(row=0, column=11, padx=8, pady=4)

        # Paso 3: Panel inferior fijo con Folio, Tipo de Cambio y Totales en Vivo
        bottom_card = ctk.CTkFrame(
            self.tab_proforma, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        bottom_card.pack(fill="x", side="bottom", pady=(6, 0))

        row_inputs = ctk.CTkFrame(bottom_card, fg_color="transparent")
        row_inputs.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            row_inputs,
            text="PASO 3 • Datos de Emisión:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_NAVY,
        ).grid(row=0, column=0, padx=(2, 8), pady=3)

        self.prof_folio = self._labeled_entry(row_inputs, "Folio Proforma:", 0, 1, width=185)
        self.prof_fecha_em = self._labeled_entry(row_inputs, "Fecha Emisión:", 0, 3, width=98)
        self.prof_fecha_em.insert(0, date.today().isoformat())

        self.prof_clasif = self._labeled_entry(row_inputs, "Clasificación:", 0, 5, width=65)
        self.prof_clasif.insert(0, "F/V")

        self.prof_dolar = self._labeled_entry(row_inputs, "Dólar Obs. (CLP):", 0, 7, width=85)
        self.prof_dolar.insert(0, "981.08")
        self.prof_dolar.bind("<KeyRelease>", lambda _e: self._update_proforma_totals_ui())

        self.prof_dcto = self._labeled_entry(row_inputs, "Descuento USD:", 0, 9, width=75)
        self.prof_dcto.insert(0, "0.00")
        self.prof_dcto.bind("<KeyRelease>", lambda _e: self._update_proforma_totals_ui())

        self.prof_otros = self._labeled_entry(row_inputs, "Otros USD:", 0, 11, width=75)
        self.prof_otros.insert(0, "0.00")
        self.prof_otros.bind("<KeyRelease>", lambda _e: self._update_proforma_totals_ui())

        row_totals = ctk.CTkFrame(bottom_card, fg_color="#F8FAFC", corner_radius=8)
        row_totals.pack(fill="x", padx=10, pady=(2, 8))

        self.prof_totals_lbl = ctk.CTkLabel(
            row_totals,
            text="Subtotal: $0.00 USD   |   IVA (19%): $0.00 USD   |   TOTAL PROFORMA: $0.00 USD   ($0 CLP)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_NAVY,
        )
        self.prof_totals_lbl.pack(side="left", padx=12, pady=8)

        ctk.CTkButton(
            row_totals,
            text="🚀 Emitir Proforma (Excel + PDF)",
            width=235,
            height=36,
            fg_color=COLOR_NAVY,
            hover_color="#25477A",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._emit_proforma,
        ).pack(side="right", padx=10, pady=6)

        # Paso 2: Tabla central interactiva
        mid_card = ctk.CTkFrame(
            self.tab_proforma, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        mid_card.pack(fill="both", expand=True)

        mid_header = ctk.CTkFrame(mid_card, fg_color="#F8FAFC", corner_radius=6, height=30)
        mid_header.pack(fill="x", padx=6, pady=(6, 2))
        self.prof_step2_lbl = ctk.CTkLabel(
            mid_header,
            text="PASO 2 • Haz clic sobre las maniobras para incluirlas [✓] o excluirlas [ ] de la Proforma:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.prof_step2_lbl.pack(side="left", padx=10, pady=4)

        p_cols = ("sel", "id", "fecha", "horario", "tt", "nave", "servicio", "lancha", "total_usd", "proforma_smc")
        self.prof_tree = ttk.Treeview(mid_card, columns=p_cols, show="headings", height=10)
        self._configure_tree_tags(self.prof_tree)

        for col, title, w in [
            ("sel", "INCLUIR", 65),
            ("id", "ID", 45),
            ("fecha", "FECHA", 95),
            ("horario", "HORARIO (INICIO - TÉRMINO)", 165),
            ("tt", "TT", 75),
            ("nave", "NAVE ATENDIDA", 160),
            ("servicio", "TIPO SERVICIO", 160),
            ("lancha", "LANCHA", 120),
            ("total_usd", "TOTAL USD", 95),
            ("proforma_smc", "PROFORMA ASIGNADA", 180),
        ]:
            self.prof_tree.heading(col, text=title)
            self.prof_tree.column(col, width=w)

        vsb = ttk.Scrollbar(mid_card, orient="vertical", command=self.prof_tree.yview)
        self.prof_tree.configure(yscrollcommand=vsb.set)
        self.prof_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=(2, 6))
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=(2, 6))
        self.prof_tree.bind("<ButtonRelease-1>", self._toggle_proforma_row)

    def _on_proforma_client_change(self) -> None:
        codigo = self.prof_cliente.get().strip()
        self.prof_folio.delete(0, "end")
        self.prof_folio.insert(0, f"SMC-PDS-IQQ-{codigo}-V0001")
        ops = self.db.list_operaciones(cliente=codigo)
        naves = sorted({op.nave for op in ops if op.nave})
        self.prof_nave.configure(values=naves if naves else [""])
        if naves:
            if "SHUN XING 17" in naves:
                self.prof_nave.set("SHUN XING 17")
            else:
                self.prof_nave.set(naves[0])
        else:
            self.prof_nave.set("")
        self._search_proforma_ops()

    def _search_proforma_ops(self) -> None:
        cliente = self.prof_cliente.get().strip()
        nave = self.prof_nave.get().strip()
        ops = self.db.list_operaciones(
            fecha_desde=self.prof_desde.get().strip() or None,
            fecha_hasta=self.prof_hasta.get().strip() or None,
            cliente=cliente or None,
            nave=nave or None,
        )
        self._proforma_ops_map = {op.id: op for op in ops if op.id is not None}
        unbilled = {op.id for op in ops if op.id is not None and not op.proforma_smc.strip()}
        self._proforma_selected_ids = unbilled if unbilled else set(self._proforma_ops_map.keys())
        self._render_proforma_tree()

    def _render_proforma_tree(self) -> None:
        self.prof_tree.delete(*self.prof_tree.get_children())
        for op_id, op in self._proforma_ops_map.items():
            is_sel = op_id in self._proforma_selected_ids
            mark = "  [✓] Sí" if is_sel else "  [ ] No"
            row_tag = "SELECTED_ROW" if is_sel else ("BILLED_ROW" if op.proforma_smc.strip() else "EVEN")
            self.prof_tree.insert(
                "",
                "end",
                iid=str(op_id),
                tags=(row_tag,),
                values=(
                    mark,
                    op.id,
                    op.fecha,
                    f"{op.hrs_inicio} a {op.hrs_termino}",
                    op.total_time,
                    op.nave,
                    op.servicio,
                    op.lancha,
                    f"${op.total_usd:,.2f}",
                    op.proforma_smc or "Sin Proforma (Disponible)",
                ),
            )
        self.prof_step2_lbl.configure(
            text=(
                f"PASO 2 • {len(self._proforma_selected_ids)} de {len(self._proforma_ops_map)} maniobras "
                "marcadas con [✓] para incluir en la Proforma (Haz clic en una fila para marcar/desmarcar):"
            )
        )
        self._update_proforma_totals_ui()

    def _toggle_proforma_row(self, event: object) -> None:
        row_id = self.prof_tree.identify_row(event.y)  # type: ignore[attr-defined]
        if not row_id:
            return
        op_id = int(row_id)
        if op_id in self._proforma_selected_ids:
            self._proforma_selected_ids.remove(op_id)
        else:
            self._proforma_selected_ids.add(op_id)
        self._render_proforma_tree()

    def _select_all_proforma(self) -> None:
        if len(self._proforma_selected_ids) == len(self._proforma_ops_map):
            self._proforma_selected_ids.clear()
        else:
            self._proforma_selected_ids = set(self._proforma_ops_map.keys())
        self._render_proforma_tree()

    def _update_proforma_totals_ui(self) -> None:
        selected_ops = [self._proforma_ops_map[i] for i in self._proforma_selected_ids if i in self._proforma_ops_map]
        try:
            dcto = float(self.prof_dcto.get() or 0.0)
            otros = float(self.prof_otros.get() or 0.0)
            dolar = float(self.prof_dolar.get() or 981.08)
        except ValueError:
            return
        totals = calculate_proforma_totals(
            [op.total_usd for op in selected_ops],
            descuento_usd=dcto,
            otros_usd=otros,
            valor_dolar_clp=dolar,
        )
        self.prof_totals_lbl.configure(
            text=(
                f"Maniobras: {len(selected_ops)}   |   "
                f"Subtotal: ${totals['subtotal_usd']:,.2f} USD   |   "
                f"IVA (19%): ${totals['iva_usd']:,.2f} USD   |   "
                f"TOTAL: ${totals['total_usd']:,.2f} USD   (${totals['total_clp']:,.0f} CLP)"
            )
        )

    def _emit_proforma(self) -> None:
        if not self._proforma_selected_ids:
            messagebox.showwarning("Sin Selección", "Seleccione al menos una maniobra para emitir la Proforma.")
            return
        cliente_cod = self.prof_cliente.get().strip()
        cliente = self.db.get_cliente_by_codigo(cliente_cod)
        if not cliente:
            messagebox.showerror("Error", f"Cliente '{cliente_cod}' no encontrado.")
            return

        selected_ops = [self._proforma_ops_map[i] for i in sorted(self._proforma_selected_ids)]
        folio = self.prof_folio.get().strip()
        nave = self.prof_nave.get().strip() or selected_ops[0].nave

        try:
            dcto = float(self.prof_dcto.get() or 0.0)
            otros = float(self.prof_otros.get() or 0.0)
            dolar = float(self.prof_dolar.get() or 981.08)
        except ValueError:
            messagebox.showerror("Error", "Los montos numéricos de Dólar, Descuento u Otros son inválidos.")
            return

        totals = calculate_proforma_totals(
            [op.total_usd for op in selected_ops],
            descuento_usd=dcto,
            otros_usd=otros,
            valor_dolar_clp=dolar,
        )
        proforma = ProformaSummary(
            folio=folio,
            fecha_emision=self.prof_fecha_em.get().strip(),
            cliente=cliente,
            nave_nombre=nave,
            nave_clasificacion=self.prof_clasif.get().strip() or "M/N",
            valor_dolar_clp=dolar,
            operaciones=selected_ops,
            descuento_usd=dcto,
            subtotal_usd=totals["subtotal_usd"],
            iva_usd=totals["iva_usd"],
            otros_usd=otros,
            total_usd=totals["total_usd"],
            total_clp_referencial=totals["total_clp"],
        )

        op_ids = [op.id for op in selected_ops if op.id is not None]
        try:
            self.db.register_proforma(proforma, op_ids, force_reissue=False)
        except DuplicateProformaError as exc:
            if not messagebox.askyesno(
                "Prevención de Doble Cobro",
                f"{exc}\n\n¿Desea forzar la re-emisión sobrescribiendo el folio asignado?",
            ):
                return
            self.db.register_proforma(proforma, op_ids, force_reissue=True)
        except ValidationError as exc:
            messagebox.showerror("Validación", str(exc))
            return

        safe_folio = folio.replace("/", "-")
        xlsx_path = generate_proforma_excel(proforma, self.export_dir / f"{safe_folio}.xlsx")
        pdf_path = generate_proforma_pdf(proforma, self.export_dir / f"{safe_folio}.pdf")

        self._refresh_all_views()
        self._search_proforma_ops()
        if messagebox.askyesno(
            "Proforma Emitida Exitosamente",
            f"Folio: {folio}\nTotal: ${proforma.total_usd:,.2f} USD\n\n"
            f"Excel: {xlsx_path.name}\nPDF: {pdf_path.name}\n\n"
            "¿Desea abrir la carpeta con los archivos generados?",
        ):
            self._open_export_folder()

    # =========================================================================
    # PESTAÑA 3: EMITIR ORDEN DE COMPRA (OC LANCHAS EXTERNAS)
    # =========================================================================
    def _build_tab_orden_compra(self) -> None:
        top_card = ctk.CTkFrame(
            self.tab_oc, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        top_card.pack(fill="x", side="top", pady=(0, 6))

        top_bar = ctk.CTkFrame(top_card, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(
            top_bar,
            text="PASO 1 • Lancha Subcontratada:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEAL,
        ).grid(row=0, column=0, padx=(4, 8), pady=4)

        self.oc_lancha = ctk.CTkComboBox(
            top_bar,
            width=165,
            height=30,
            values=["BUCA LAUREL"],
            command=lambda _v: self._search_oc_ops(),
        )
        self.oc_lancha.grid(row=0, column=1, padx=4, pady=4)

        ctk.CTkLabel(top_bar, text="Desde:").grid(row=0, column=2, padx=4, pady=4)
        self.oc_desde = ctk.CTkEntry(top_bar, width=100, height=30, placeholder_text="YYYY-MM-DD")
        self.oc_desde.grid(row=0, column=3, padx=4, pady=4)

        ctk.CTkLabel(top_bar, text="Hasta:").grid(row=0, column=4, padx=4, pady=4)
        self.oc_hasta = ctk.CTkEntry(top_bar, width=100, height=30, placeholder_text="YYYY-MM-DD")
        self.oc_hasta.grid(row=0, column=5, padx=4, pady=4)

        ctk.CTkButton(
            top_bar,
            text="🔍 Buscar Pendientes OC",
            width=155,
            height=30,
            fg_color=COLOR_PRIMARY,
            command=self._search_oc_ops,
        ).grid(row=0, column=6, padx=6, pady=4)

        ctk.CTkButton(
            top_bar,
            text="🚀 Emitir Orden de Compra (Excel + PDF)",
            width=245,
            height=32,
            fg_color=COLOR_TEAL,
            hover_color=COLOR_TEAL_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._emit_orden_compra,
        ).grid(row=0, column=7, padx=8, pady=4)

        # Panel inferior fijo
        bottom_card = ctk.CTkFrame(
            self.tab_oc, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        bottom_card.pack(fill="x", side="bottom", pady=(6, 0))

        row_inputs = ctk.CTkFrame(bottom_card, fg_color="transparent")
        row_inputs.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            row_inputs,
            text="PASO 3 • Datos Orden de Compra:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEAL,
        ).grid(row=0, column=0, padx=(2, 8), pady=3)

        self.oc_folio = self._labeled_entry(row_inputs, "Folio OC:", 0, 1, width=180)
        self.oc_folio.insert(0, "SMC-OC-IQQ-BL-V001")

        self.oc_fecha_em = self._labeled_entry(row_inputs, "Fecha Emisión:", 0, 3, width=105)
        self.oc_fecha_em.insert(0, date.today().isoformat())

        self.oc_proveedor = self._labeled_entry(row_inputs, "Proveedor / Armador:", 0, 5, width=280)
        self.oc_proveedor.insert(0, "Servicios Marítimos Bucalemu / Armador Externo")

        row_totals = ctk.CTkFrame(bottom_card, fg_color="#F8FAFC", corner_radius=8)
        row_totals.pack(fill="x", padx=10, pady=(2, 8))

        self.oc_totals_lbl = ctk.CTkLabel(
            row_totals,
            text="Subtotal OC: $0.00 USD   |   IVA (19%): $0.00 USD   |   TOTAL ORDEN DE COMPRA: $0.00 USD",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_NAVY,
        )
        self.oc_totals_lbl.pack(side="left", padx=12, pady=8)

        ctk.CTkButton(
            row_totals,
            text="🚀 Emitir Orden de Compra (Excel + PDF)",
            width=255,
            height=36,
            fg_color=COLOR_TEAL,
            hover_color=COLOR_TEAL_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._emit_orden_compra,
        ).pack(side="right", padx=10, pady=6)

        # Tabla central
        mid_card = ctk.CTkFrame(
            self.tab_oc, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        mid_card.pack(fill="both", expand=True)

        mid_header = ctk.CTkFrame(mid_card, fg_color="#F8FAFC", corner_radius=6, height=30)
        mid_header.pack(fill="x", padx=6, pady=(6, 2))
        self.oc_step2_lbl = ctk.CTkLabel(
            mid_header,
            text="PASO 2 • Maniobras ejecutadas por lancha externa pendientes de Orden de Compra:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.oc_step2_lbl.pack(side="left", padx=10, pady=4)

        o_cols = ("sel", "id", "fecha", "horario", "tt", "nave", "cliente", "servicio", "lancha", "total_usd")
        self.oc_tree = ttk.Treeview(mid_card, columns=o_cols, show="headings", height=10)
        self._configure_tree_tags(self.oc_tree)

        for col, title, w in [
            ("sel", "INCLUIR", 65),
            ("id", "ID", 45),
            ("fecha", "FECHA", 95),
            ("horario", "HORARIO", 155),
            ("tt", "TT", 75),
            ("nave", "NAVE ATENDIDA", 160),
            ("cliente", "AGENCIA CLIENTE", 115),
            ("servicio", "TIPO SERVICIO", 160),
            ("lancha", "LANCHA EXTERNA", 125),
            ("total_usd", "COSTO USD", 95),
        ]:
            self.oc_tree.heading(col, text=title)
            self.oc_tree.column(col, width=w)

        vsb = ttk.Scrollbar(mid_card, orient="vertical", command=self.oc_tree.yview)
        self.oc_tree.configure(yscrollcommand=vsb.set)
        self.oc_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=(2, 6))
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=(2, 6))
        self.oc_tree.bind("<ButtonRelease-1>", self._toggle_oc_row)

    def _search_oc_ops(self) -> None:
        lancha = self.oc_lancha.get().strip()
        ops = self.db.list_operaciones(
            fecha_desde=self.oc_desde.get().strip() or None,
            fecha_hasta=self.oc_hasta.get().strip() or None,
            lancha=lancha or None,
            solo_lancha_externa_pendiente_oc=True,
        )
        self._oc_ops_map = {op.id: op for op in ops if op.id is not None}
        self._oc_selected_ids = set(self._oc_ops_map.keys())
        self._render_oc_tree()

    def _render_oc_tree(self) -> None:
        self.oc_tree.delete(*self.oc_tree.get_children())
        for op_id, op in self._oc_ops_map.items():
            is_sel = op_id in self._oc_selected_ids
            mark = "  [✓] Sí" if is_sel else "  [ ] No"
            self.oc_tree.insert(
                "",
                "end",
                iid=str(op_id),
                tags=("SELECTED_ROW" if is_sel else "EVEN",),
                values=(
                    mark,
                    op.id,
                    op.fecha,
                    f"{op.hrs_inicio} a {op.hrs_termino}",
                    op.total_time,
                    op.nave,
                    op.cliente,
                    op.servicio,
                    op.lancha,
                    f"${op.total_usd:,.2f}",
                ),
            )
        selected_ops = [self._oc_ops_map[i] for i in self._oc_selected_ids if i in self._oc_ops_map]
        totals = calculate_proforma_totals([op.total_usd for op in selected_ops])
        self.oc_step2_lbl.configure(
            text=(
                f"PASO 2 • {len(selected_ops)} de {len(self._oc_ops_map)} maniobras de lancha externa "
                "seleccionadas para liquidación de pago:"
            )
        )
        self.oc_totals_lbl.configure(
            text=(
                f"Maniobras: {len(selected_ops)}   |   "
                f"Subtotal OC: ${totals['subtotal_usd']:,.2f} USD   |   "
                f"IVA (19%): ${totals['iva_usd']:,.2f} USD   |   "
                f"TOTAL OC: ${totals['total_usd']:,.2f} USD"
            )
        )

    def _toggle_oc_row(self, event: object) -> None:
        row_id = self.oc_tree.identify_row(event.y)  # type: ignore[attr-defined]
        if not row_id:
            return
        op_id = int(row_id)
        if op_id in self._oc_selected_ids:
            self._oc_selected_ids.remove(op_id)
        else:
            self._oc_selected_ids.add(op_id)
        self._render_oc_tree()

    def _emit_orden_compra(self) -> None:
        if not self._oc_selected_ids:
            messagebox.showwarning("Sin Selección", "Seleccione al menos una maniobra de lancha externa.")
            return
        selected_ops = [self._oc_ops_map[i] for i in sorted(self._oc_selected_ids)]
        folio_oc = self.oc_folio.get().strip()
        totals = calculate_proforma_totals([op.total_usd for op in selected_ops])

        oc = OrdenCompraSummary(
            folio_oc=folio_oc,
            fecha_emision=self.oc_fecha_em.get().strip(),
            proveedor_nombre=self.oc_proveedor.get().strip(),
            lancha_nombre=self.oc_lancha.get().strip(),
            operaciones=selected_ops,
            subtotal_usd=totals["subtotal_usd"],
            iva_usd=totals["iva_usd"],
            total_usd=totals["total_usd"],
        )

        op_ids = [op.id for op in selected_ops if op.id is not None]
        try:
            self.db.register_orden_compra(oc, op_ids)
        except (DuplicateOrdenCompraError, ValidationError) as exc:
            messagebox.showerror("Error en Orden de Compra", str(exc))
            return

        safe_folio = folio_oc.replace("/", "-")
        xlsx_path = generate_orden_compra_excel(oc, self.export_dir / f"{safe_folio}.xlsx")
        pdf_path = generate_orden_compra_pdf(oc, self.export_dir / f"{safe_folio}.pdf")

        self._refresh_all_views()
        self._search_oc_ops()
        if messagebox.askyesno(
            "Orden de Compra Emitida",
            f"Folio OC: {folio_oc}\nTotal OC: ${oc.total_usd:,.2f} USD\n\n"
            f"Excel: {xlsx_path.name}\nPDF: {pdf_path.name}\n\n"
            "¿Desea abrir la carpeta con los archivos generados?",
        ):
            self._open_export_folder()

    # =========================================================================
    # PESTAÑA 4: TARIFARIOS Y DASHBOARD EJECUTIVO
    # =========================================================================
    def _build_tab_tarifas_resumen(self) -> None:
        self.tab_tarifas.grid_columnconfigure(0, weight=5)
        self.tab_tarifas.grid_columnconfigure(1, weight=6)
        self.tab_tarifas.grid_rowconfigure(0, weight=1)

        # Panel Izquierdo: Matriz Tarifaria
        left = ctk.CTkFrame(
            self.tab_tarifas, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            left,
            text="💲 Catálogo de Tarifarios por Cliente (USD)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_NAVY,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        t_form = ctk.CTkFrame(left, fg_color="#F8FAFC", corner_radius=8)
        t_form.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(t_form, text="Cliente:").grid(row=0, column=0, padx=4, pady=6)
        self.tar_cliente = ctk.CTkComboBox(t_form, width=115, height=28, values=["LBH"])
        self.tar_cliente.grid(row=0, column=1, padx=4, pady=6)

        ctk.CTkLabel(t_form, text="Servicio:").grid(row=0, column=2, padx=4, pady=6)
        self.tar_servicio = ctk.CTkComboBox(t_form, width=155, height=28, values=SERVICIOS_COMUNES)
        self.tar_servicio.grid(row=0, column=3, padx=4, pady=6)

        self.tar_valor = self._labeled_entry(t_form, "USD:", 0, 4, width=75)
        ctk.CTkButton(
            t_form, text="💾 Guardar", width=90, height=28, fg_color=COLOR_SUCCESS, command=self._save_tariff
        ).grid(row=0, column=6, padx=6, pady=6)

        self.tar_tree = ttk.Treeview(left, columns=("cliente", "servicio", "valor_usd"), show="headings")
        self._configure_tree_tags(self.tar_tree)
        self.tar_tree.heading("cliente", text="AGENCIA CLIENTE")
        self.tar_tree.heading("servicio", text="TIPO DE SERVICIO")
        self.tar_tree.heading("valor_usd", text="TARIFA BASE USD")
        self.tar_tree.column("cliente", width=115)
        self.tar_tree.column("servicio", width=210)
        self.tar_tree.column("valor_usd", width=110, anchor="e")
        self.tar_tree.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.tar_tree.bind("<<TreeviewSelect>>", self._on_tariff_select)

        # Panel Derecho: Dashboard Gráfico de Barras + Reporte Ejecutivo
        right = ctk.CTkFrame(
            self.tab_tarifas, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        top_r = ctk.CTkFrame(right, fg_color="transparent")
        top_r.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            top_r,
            text="📊 Distribución Comercial por Agencia y Flota",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_NAVY,
        ).pack(side="left")
        ctk.CTkButton(
            top_r, text="🔄 Actualizar", width=100, height=28, fg_color=COLOR_PRIMARY, command=self._load_summary_panel
        ).pack(side="right")

        self.bars_container = ctk.CTkFrame(right, fg_color="#F8FAFC", corner_radius=8)
        self.bars_container.pack(fill="x", padx=10, pady=4)

        self.summary_box = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=11))
        self.summary_box.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    def _on_tariff_select(self, _event: object) -> None:
        sel = self.tar_tree.selection()
        if not sel:
            return
        vals = self.tar_tree.item(sel[0], "values")
        if vals:
            self.tar_cliente.set(vals[0])
            self.tar_servicio.set(vals[1])
            self.tar_valor.delete(0, "end")
            self.tar_valor.insert(0, str(vals[2]).replace("$", "").replace(",", ""))

    def _save_tariff(self) -> None:
        try:
            cliente = self.tar_cliente.get().strip()
            servicio = self.tar_servicio.get().strip()
            val = float(self.tar_valor.get().strip())
            self.db.upsert_tariff(cliente, servicio, val)
            self._load_tariffs_table()
            messagebox.showinfo("Tarifario Actualizado", f"{cliente} | {servicio}: ${val:.2f} USD")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _load_tariffs_table(self) -> None:
        self.tar_tree.delete(*self.tar_tree.get_children())
        for idx, t in enumerate(self.db.list_tariffs()):
            tag = "EVEN" if idx % 2 == 0 else "ODD"
            self.tar_tree.insert("", "end", tags=(tag,), values=(t.codigo_agencia, t.servicio, f"${t.valor_usd:,.2f}"))

    def _load_summary_panel(self) -> None:
        summary = self.db.get_operations_summary()

        # Actualizar barras de progreso visuales por cliente
        for child in self.bars_container.winfo_children():
            child.destroy()

        total_ops = sum(int(r["cantidad"] or 0) for r in summary["por_cliente"])
        total_usd = sum(float(r["total_usd"] or 0.0) for r in summary["por_cliente"])

        for row in summary["por_cliente"][:5]:
            cname = str(row["cliente"])
            qty = int(row["cantidad"] or 0)
            usd = float(row["total_usd"] or 0.0)
            ratio = (usd / total_usd) if total_usd > 0 else 0.0

            b_row = ctk.CTkFrame(self.bars_container, fg_color="transparent")
            b_row.pack(fill="x", padx=10, pady=3)

            ctk.CTkLabel(
                b_row, text=f"{cname} ({qty})", width=120, anchor="w", font=ctk.CTkFont(size=11, weight="bold")
            ).pack(side="left")

            pbar = ctk.CTkProgressBar(b_row, height=10, progress_color=COLOR_PRIMARY)
            pbar.pack(side="left", fill="x", expand=True, padx=8)
            pbar.set(ratio)

            ctk.CTkLabel(
                b_row,
                text=f"${usd:,.0f} USD ({ratio * 100:.1f}%)",
                width=145,
                anchor="e",
                font=ctk.CTkFont(size=11),
            ).pack(side="right")

        lines: list[str] = []
        lines.append("=== RESUMEN POR CLIENTE / AGENCIA ===")
        lines.append(f"{'CLIENTE':<18} {'MANIOBRAS':>10} {'TOTAL USD':>16}")
        lines.append("-" * 46)
        for row in summary["por_cliente"]:
            qty = int(row["cantidad"] or 0)
            usd = float(row["total_usd"] or 0.0)
            lines.append(f"{str(row['cliente']):<18} {qty:>10d} ${usd:>14,.2f}")
        lines.append("-" * 46)
        lines.append(f"{'TOTAL GENERAL':<18} {total_ops:>10d} ${total_usd:>14,.2f}\n")

        lines.append("=== RESUMEN POR LANCHA (FLOTA PROPIA VS EXTERNA) ===")
        lines.append(f"{'LANCHA':<18} {'MANIOBRAS':>10} {'TOTAL USD':>16}")
        lines.append("-" * 46)
        for row in summary["por_lancha"]:
            lines.append(
                f"{str(row['lancha']):<18} {int(row['cantidad'] or 0):>10d} ${float(row['total_usd'] or 0.0):>14,.2f}"
            )
        lines.append("")

        lines.append("=== RESUMEN POR TIPO DE SERVICIO ===")
        lines.append(f"{'SERVICIO':<26} {'MANIOBRAS':>10} {'TOTAL USD':>14}")
        lines.append("-" * 52)
        for row in summary["por_servicio"]:
            lines.append(
                f"{str(row['servicio']):<26} {int(row['cantidad'] or 0):>10d} ${float(row['total_usd'] or 0.0):>12,.2f}"
            )

        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", "\n".join(lines))
        self.summary_box.configure(state="disabled")

    def _update_kpi_cards(self) -> None:
        """Actualiza los 4 indicadores superiores en tiempo real."""
        all_ops = self.db.list_operaciones()
        total_ops = len(all_ops)
        total_usd = sum(o.total_usd for o in all_ops)
        sin_proforma = sum(1 for o in all_ops if not o.proforma_smc.strip() and o.estado != "INTERNO")
        pend_oc = len(self.db.list_operaciones(solo_lancha_externa_pendiente_oc=True))

        self.kpi_ops_val.configure(text=f"{total_ops:,}")
        self.kpi_usd_val.configure(text=f"${total_usd:,.2f}")
        self.kpi_pending_prof_val.configure(text=f"{sin_proforma:,}")
        self.kpi_pending_oc_val.configure(text=f"{pend_oc:,}")

    def _refresh_all_views(self) -> None:
        clientes = [c.codigo_agencia for c in self.db.list_clientes()]
        lanchas_all = [l.nombre for l in self.db.list_lanchas()]
        lanchas_ext = [l.nombre for l in self.db.list_lanchas(solo_externas=True)]

        self.flt_cliente.configure(values=["TODOS", *clientes])
        self.op_cliente.configure(values=clientes)
        if clientes and self.op_cliente.get() not in clientes:
            self.op_cliente.set("LBH" if "LBH" in clientes else clientes[0])

        self.flt_lancha.configure(values=["TODAS", *lanchas_all])
        self.op_lancha.configure(values=lanchas_all)

        self.prof_cliente.configure(values=clientes)
        if clientes and self.prof_cliente.get() not in clientes:
            self.prof_cliente.set("LBH" if "LBH" in clientes else clientes[0])
        self._on_proforma_client_change()

        if lanchas_ext:
            self.oc_lancha.configure(values=lanchas_ext)
            if self.oc_lancha.get() not in lanchas_ext:
                self.oc_lancha.set(lanchas_ext[0])
        self._search_oc_ops()

        self.tar_cliente.configure(values=clientes)
        if clientes and self.tar_cliente.get() not in clientes:
            self.tar_cliente.set("LBH" if "LBH" in clientes else clientes[0])

        self._update_kpi_cards()
        self._load_operations_table()
        self._load_tariffs_table()
        self._load_summary_panel()


def main() -> None:
    """Punto de entrada de la interfaz gráfica."""
    app = SMCOperacionesApp()
    app.mainloop()


if __name__ == "__main__":
    main()
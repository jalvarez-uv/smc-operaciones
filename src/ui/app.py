"""Interfaz gráfica de escritorio en CustomTkinter para SMC-Operaciones."""

from __future__ import annotations

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


class SMCOperacionesApp(ctk.CTk):
    """Aplicación principal de escritorio de Servicios Marítimos Carrere (SMC)."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        super().__init__()

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.data_dir = Path(data_dir) if data_dir else Path("data")
        self.export_dir = self.data_dir / "export"
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self.db = db_manager or DatabaseManager(self.data_dir / "smc_operaciones.db")
        self.db.init_db()

        self.title("Servicios Marítimos Carrere (SMC) — Operaciones, Proformas y OC")
        self.geometry("1240x680")
        self.minsize(960, 560)
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
        self._build_header()
        self._build_tabs()
        self._refresh_all_views()

    def _maximize_window(self) -> None:
        """Maximiza la ventana de forma compatible con Linux Mint y Windows."""
        try:
            if sys.platform.startswith("linux"):
                self.attributes("-zoomed", True)
            else:
                self.state("zoomed")
        except Exception:
            pass

    def _toggle_fullscreen(self, _event: object = None) -> None:
        """Alterna pantalla completa con F11 o desde el botón del encabezado."""
        self._is_fullscreen = not self._is_fullscreen
        try:
            self.attributes("-fullscreen", self._is_fullscreen)
        except Exception:
            pass

    def _configure_treeview_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground="#111827",
            rowheight=24,
            fieldbackground="#FFFFFF",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#1B365D",
            foreground="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Treeview", background=[("selected", "#2563EB")], foreground=[("selected", "#FFFFFF")])

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="#1B365D", corner_radius=0, height=50)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="SERVICIOS MARÍTIMOS CARRERE (SMC) — IQUIQUE",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF",
        ).pack(side="left", padx=16, pady=8)

        ctk.CTkButton(
            header,
            text="Pantalla Completa (F11)",
            width=155,
            height=28,
            fg_color="#334155",
            hover_color="#475569",
            command=self._toggle_fullscreen,
        ).pack(side="right", padx=14, pady=8)

        ctk.CTkLabel(
            header,
            text="Control de Operaciones  |  Proformas de Servicio  |  Órdenes de Compra",
            font=ctk.CTkFont(size=11),
            text_color="#CBD5E1",
        ).pack(side="right", padx=12, pady=8)

    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self.tab_ops = self.tabview.add("1. Control de Operaciones")
        self.tab_proforma = self.tabview.add("2. Emitir Proforma de Servicios")
        self.tab_oc = self.tabview.add("3. Emitir Orden de Compra (OC Lanchas)")
        self.tab_tarifas = self.tabview.add("4. Tarifarios y Resumen")

        self._build_tab_operaciones()
        self._build_tab_proforma()
        self._build_tab_orden_compra()
        self._build_tab_tarifas_resumen()

    # =========================================================================
    # PESTAÑA 1: CONTROL DE OPERACIONES
    # =========================================================================
    def _build_tab_operaciones(self) -> None:
        filter_frame = ctk.CTkFrame(self.tab_ops)
        filter_frame.pack(fill="x", side="top", padx=4, pady=(2, 4))

        ctk.CTkLabel(filter_frame, text="Desde:").grid(row=0, column=0, padx=3, pady=4)
        self.flt_desde = ctk.CTkEntry(filter_frame, width=95, placeholder_text="YYYY-MM-DD")
        self.flt_desde.grid(row=0, column=1, padx=3, pady=4)

        ctk.CTkLabel(filter_frame, text="Hasta:").grid(row=0, column=2, padx=3, pady=4)
        self.flt_hasta = ctk.CTkEntry(filter_frame, width=95, placeholder_text="YYYY-MM-DD")
        self.flt_hasta.grid(row=0, column=3, padx=3, pady=4)

        ctk.CTkLabel(filter_frame, text="Nave:").grid(row=0, column=4, padx=3, pady=4)
        self.flt_nave = ctk.CTkEntry(filter_frame, width=120, placeholder_text="Buscar nave...")
        self.flt_nave.grid(row=0, column=5, padx=3, pady=4)

        ctk.CTkLabel(filter_frame, text="Cliente:").grid(row=0, column=6, padx=3, pady=4)
        self.flt_cliente = ctk.CTkComboBox(filter_frame, width=115, values=["TODOS"])
        self.flt_cliente.set("TODOS")
        self.flt_cliente.grid(row=0, column=7, padx=3, pady=4)

        ctk.CTkLabel(filter_frame, text="Lancha:").grid(row=0, column=8, padx=3, pady=4)
        self.flt_lancha = ctk.CTkComboBox(filter_frame, width=125, values=["TODAS"])
        self.flt_lancha.set("TODAS")
        self.flt_lancha.grid(row=0, column=9, padx=3, pady=4)

        ctk.CTkLabel(filter_frame, text="Estado:").grid(row=0, column=10, padx=3, pady=4)
        self.flt_estado = ctk.CTkComboBox(filter_frame, width=105, values=["TODOS", *ESTADOS_OP])
        self.flt_estado.set("TODOS")
        self.flt_estado.grid(row=0, column=11, padx=3, pady=4)

        ctk.CTkButton(filter_frame, text="Filtrar", width=75, command=self._load_operations_table).grid(
            row=0, column=12, padx=3, pady=4
        )
        ctk.CTkButton(
            filter_frame,
            text="Limpiar",
            width=70,
            fg_color="#64748B",
            command=self._clear_filters,
        ).grid(row=0, column=13, padx=3, pady=4)

        form_frame = ctk.CTkFrame(self.tab_ops)
        form_frame.pack(fill="x", side="top", padx=4, pady=(0, 4))

        self.op_fecha = self._labeled_entry(form_frame, "Fecha:", 0, 0, width=100)
        self.op_fecha.insert(0, date.today().isoformat())

        self.op_inicio = self._labeled_entry(form_frame, "Hrs Inicio:", 0, 2, width=80)
        self.op_inicio.insert(0, "08:00:00")
        self.op_inicio.bind("<FocusOut>", lambda _e: self._recalculate_form_values())

        self.op_termino = self._labeled_entry(form_frame, "Hrs Término:", 0, 4, width=80)
        self.op_termino.insert(0, "09:00:00")
        self.op_termino.bind("<FocusOut>", lambda _e: self._recalculate_form_values())

        self.op_tt = self._labeled_entry(form_frame, "Total Time:", 0, 6, width=80)
        self.op_tt.insert(0, "01:00:00")

        self.op_nave = self._labeled_entry(form_frame, "Nave:", 0, 8, width=140)

        ctk.CTkLabel(form_frame, text="Cliente:").grid(row=0, column=10, padx=3, pady=3, sticky="e")
        self.op_cliente = ctk.CTkComboBox(
            form_frame,
            width=115,
            values=["LBH"],
            command=lambda _v: self._autofill_tariff(),
        )
        self.op_cliente.grid(row=0, column=11, padx=3, pady=3)

        ctk.CTkLabel(form_frame, text="Servicio:").grid(row=1, column=0, padx=3, pady=3, sticky="e")
        self.op_servicio = ctk.CTkComboBox(
            form_frame,
            width=150,
            values=SERVICIOS_COMUNES,
            command=lambda _v: self._autofill_tariff(),
        )
        self.op_servicio.grid(row=1, column=1, padx=3, pady=3)

        ctk.CTkLabel(form_frame, text="Terminal:").grid(row=1, column=2, padx=3, pady=3, sticky="e")
        self.op_terminal = ctk.CTkComboBox(form_frame, width=95, values=TERMINALES_IQQ)
        self.op_terminal.set("GIRA")
        self.op_terminal.grid(row=1, column=3, padx=3, pady=3)

        ctk.CTkLabel(form_frame, text="Lancha:").grid(row=1, column=4, padx=3, pady=3, sticky="e")
        self.op_lancha = ctk.CTkComboBox(form_frame, width=125, values=["DOÑA RENATA", "BUCA LAUREL"])
        self.op_lancha.set("DOÑA RENATA")
        self.op_lancha.grid(row=1, column=5, padx=3, pady=3)

        self.op_valor = self._labeled_entry(form_frame, "Valor USD:", 1, 6, width=80)
        self.op_valor.insert(0, "0.00")
        self.op_valor.bind("<KeyRelease>", lambda _e: self._recalculate_form_values())

        self.op_extra = self._labeled_entry(form_frame, "Extra USD:", 1, 8, width=80)
        self.op_extra.insert(0, "0.00")
        self.op_extra.bind("<KeyRelease>", lambda _e: self._recalculate_form_values())

        self.op_total = self._labeled_entry(form_frame, "Total USD:", 1, 10, width=85)
        self.op_total.insert(0, "0.00")

        ctk.CTkLabel(form_frame, text="Estado:").grid(row=2, column=0, padx=3, pady=3, sticky="e")
        self.op_estado = ctk.CTkComboBox(form_frame, width=110, values=ESTADOS_OP)
        self.op_estado.set("PENDIENTE")
        self.op_estado.grid(row=2, column=1, padx=3, pady=3)

        self.op_obs = self._labeled_entry(form_frame, "Observaciones:", 2, 2, width=140)
        self.op_proforma = self._labeled_entry(form_frame, "Proforma SMC:", 2, 4, width=140)
        self.op_oc_cte = self._labeled_entry(form_frame, "OC Cte:", 2, 6, width=90)
        self.op_factura = self._labeled_entry(form_frame, "Factura SMC:", 2, 8, width=90)
        self.op_lbh_ag = self._labeled_entry(form_frame, "LBH Agenc.:", 2, 10, width=90)

        btn_frame = ctk.CTkFrame(self.tab_ops, fg_color="transparent")
        btn_frame.pack(fill="x", side="top", padx=4, pady=(0, 4))

        ctk.CTkButton(btn_frame, text="Guardar Nueva", width=120, fg_color="#16A34A", command=self._save_new_op).pack(
            side="left", padx=3
        )
        ctk.CTkButton(btn_frame, text="Actualizar Seleccionada", width=155, command=self._update_selected_op).pack(
            side="left", padx=3
        )
        ctk.CTkButton(
            btn_frame, text="Eliminar", width=90, fg_color="#DC2626", command=self._delete_selected_op
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            btn_frame, text="Limpiar Formulario", width=125, fg_color="#64748B", command=self._reset_op_form
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            btn_frame, text="Exportar Vista a Excel", width=155, fg_color="#1B365D", command=self._export_current_view
        ).pack(side="right", padx=3)
        ctk.CTkButton(
            btn_frame, text="Importar Excel Base", width=150, fg_color="#0F766E", command=self._import_excel_dialog
        ).pack(side="right", padx=3)

        table_frame = ctk.CTkFrame(self.tab_ops)
        table_frame.pack(fill="both", expand=True, padx=4, pady=(0, 2))

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
        self.ops_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse", height=12)

        headers_map = {
            "id": ("ID", 45),
            "fecha": ("FECHA", 85),
            "hrs_inicio": ("HRS INICIO", 78),
            "hrs_termino": ("HRS TERMINO", 82),
            "total_time": ("TOTAL TIME", 78),
            "nave": ("NAVE", 140),
            "cliente": ("CLIENTE", 90),
            "servicio": ("SERVICIO", 125),
            "terminal": ("TERMINAL", 80),
            "lancha": ("LANCHA", 105),
            "valor_usd": ("VALOR USD", 78),
            "extra_usd": ("EXTRA USD", 78),
            "total_usd": ("TOTAL USD", 82),
            "observaciones": ("OBSERVACIONES", 125),
            "estado": ("ESTADO", 80),
            "proforma_smc": ("PROFORMA SMC", 155),
            "oc_cte": ("OC CTE", 80),
            "factura_smc": ("FACTURA SMC", 90),
            "lbh_agenciamiento": ("LBH AGENC.", 95),
        }
        for col_id, (title, width) in headers_map.items():
            self.ops_tree.heading(col_id, text=title)
            self.ops_tree.column(col_id, width=width, minwidth=45)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.ops_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.ops_tree.xview)
        self.ops_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.ops_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.ops_tree.bind("<<TreeviewSelect>>", self._on_op_select)

    def _labeled_entry(
        self, parent: ctk.CTkFrame, label: str, row: int, col: int, width: int = 120
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=col, padx=3, pady=3, sticky="e")
        entry = ctk.CTkEntry(parent, width=width)
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
            messagebox.showinfo("Actualizado", "Maniobra actualizada correctamente.")
        except Exception as exc:
            messagebox.showerror("Error al Actualizar", str(exc))

    def _delete_selected_op(self) -> None:
        if self._selected_op_id is None:
            messagebox.showwarning("Selección", "Seleccione una operación de la tabla primero.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar maniobra ID {self._selected_op_id}?"):
            self.db.delete_operacion(self._selected_op_id)
            self._reset_op_form()
            self._refresh_all_views()

    def _reset_op_form(self) -> None:
        self._selected_op_id = None
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
        for op in self._get_filtered_ops():
            self.ops_tree.insert(
                "",
                "end",
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
                    f"{op.valor_usd:.2f}",
                    f"{op.extra_usd:.2f}",
                    f"{op.total_usd:.2f}",
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
    # PESTAÑA 2: EMITIR PROFORMA DE SERVICIOS
    # =========================================================================
    def _build_tab_proforma(self) -> None:
        # 1. Barra superior de filtros y botón directo de emisión
        top_bar = ctk.CTkFrame(self.tab_proforma)
        top_bar.pack(fill="x", side="top", padx=4, pady=4)

        ctk.CTkLabel(top_bar, text="Cliente:").grid(row=0, column=0, padx=4, pady=5)
        self.prof_cliente = ctk.CTkComboBox(
            top_bar,
            width=125,
            values=["LBH"],
            command=lambda _v: self._on_proforma_client_change(),
        )
        self.prof_cliente.grid(row=0, column=1, padx=4, pady=5)

        ctk.CTkLabel(top_bar, text="Nave:").grid(row=0, column=2, padx=4, pady=5)
        self.prof_nave = ctk.CTkComboBox(
            top_bar,
            width=210,
            values=[""],
            command=lambda _v: self._search_proforma_ops(),
        )
        self.prof_nave.grid(row=0, column=3, padx=4, pady=5)

        ctk.CTkLabel(top_bar, text="Desde:").grid(row=0, column=4, padx=4, pady=5)
        self.prof_desde = ctk.CTkEntry(top_bar, width=95, placeholder_text="YYYY-MM-DD")
        self.prof_desde.grid(row=0, column=5, padx=4, pady=5)

        ctk.CTkLabel(top_bar, text="Hasta:").grid(row=0, column=6, padx=4, pady=5)
        self.prof_hasta = ctk.CTkEntry(top_bar, width=95, placeholder_text="YYYY-MM-DD")
        self.prof_hasta.grid(row=0, column=7, padx=4, pady=5)

        ctk.CTkButton(top_bar, text="Buscar Maniobras", width=125, command=self._search_proforma_ops).grid(
            row=0, column=8, padx=4, pady=5
        )
        ctk.CTkButton(
            top_bar, text="Sel. Todas", width=85, fg_color="#475569", command=self._select_all_proforma
        ).grid(row=0, column=9, padx=4, pady=5)

        ctk.CTkButton(
            top_bar,
            text="Emitir Proforma (Excel + PDF)",
            width=195,
            fg_color="#16A34A",
            hover_color="#15803D",
            command=self._emit_proforma,
        ).grid(row=0, column=10, padx=6, pady=5)

        # 2. Panel inferior fijo (empaquetado con side="bottom" ANTES de la tabla para que nunca se oculte)
        bottom_panel = ctk.CTkFrame(self.tab_proforma)
        bottom_panel.pack(fill="x", side="bottom", padx=4, pady=4)

        row_inputs = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row_inputs.pack(fill="x", padx=4, pady=(4, 2))

        self.prof_folio = self._labeled_entry(row_inputs, "Folio Proforma:", 0, 0, width=185)
        self.prof_fecha_em = self._labeled_entry(row_inputs, "Fecha Emisión:", 0, 2, width=100)
        self.prof_fecha_em.insert(0, date.today().isoformat())

        self.prof_clasif = self._labeled_entry(row_inputs, "Clasificación:", 0, 4, width=65)
        self.prof_clasif.insert(0, "F/V")

        self.prof_dolar = self._labeled_entry(row_inputs, "Valor Dólar CLP:", 0, 6, width=85)
        self.prof_dolar.insert(0, "981.08")
        self.prof_dolar.bind("<KeyRelease>", lambda _e: self._update_proforma_totals_ui())

        self.prof_dcto = self._labeled_entry(row_inputs, "Descuento USD:", 0, 8, width=75)
        self.prof_dcto.insert(0, "0.00")
        self.prof_dcto.bind("<KeyRelease>", lambda _e: self._update_proforma_totals_ui())

        self.prof_otros = self._labeled_entry(row_inputs, "Otros USD:", 0, 10, width=75)
        self.prof_otros.insert(0, "0.00")
        self.prof_otros.bind("<KeyRelease>", lambda _e: self._update_proforma_totals_ui())

        row_totals = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row_totals.pack(fill="x", padx=8, pady=(2, 6))

        self.prof_totals_lbl = ctk.CTkLabel(
            row_totals,
            text="Subtotal: $0.00 USD  |  IVA (19%): $0.00 USD  |  TOTAL: $0.00 USD  ($0 CLP)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1B365D",
        )
        self.prof_totals_lbl.pack(side="left", padx=4)

        ctk.CTkButton(
            row_totals,
            text="Emitir Proforma (Excel + PDF)",
            width=220,
            height=34,
            fg_color="#1B365D",
            command=self._emit_proforma,
        ).pack(side="right", padx=6)

        # 3. Tabla central de maniobras seleccionables
        mid_frame = ctk.CTkFrame(self.tab_proforma)
        mid_frame.pack(fill="both", expand=True, padx=4, pady=(0, 2))

        p_cols = ("sel", "id", "fecha", "horario", "tt", "nave", "servicio", "lancha", "total_usd", "proforma_smc")
        self.prof_tree = ttk.Treeview(mid_frame, columns=p_cols, show="headings", height=10)
        for col, title, w in [
            ("sel", "SEL", 45),
            ("id", "ID", 45),
            ("fecha", "FECHA", 90),
            ("horario", "HORARIO", 145),
            ("tt", "TT", 75),
            ("nave", "NAVE", 155),
            ("servicio", "SERVICIO", 155),
            ("lancha", "LANCHA", 115),
            ("total_usd", "TOTAL USD", 90),
            ("proforma_smc", "PROFORMA ACTUAL", 175),
        ]:
            self.prof_tree.heading(col, text=title)
            self.prof_tree.column(col, width=w)

        vsb = ttk.Scrollbar(mid_frame, orient="vertical", command=self.prof_tree.yview)
        self.prof_tree.configure(yscrollcommand=vsb.set)
        self.prof_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
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
        # Selecciona por defecto las pendientes; si todas tienen proforma, las selecciona igual para previsualizar
        unbilled = {op.id for op in ops if op.id is not None and not op.proforma_smc.strip()}
        self._proforma_selected_ids = unbilled if unbilled else set(self._proforma_ops_map.keys())
        self._render_proforma_tree()

    def _render_proforma_tree(self) -> None:
        self.prof_tree.delete(*self.prof_tree.get_children())
        for op_id, op in self._proforma_ops_map.items():
            mark = "[✓]" if op_id in self._proforma_selected_ids else "[ ]"
            self.prof_tree.insert(
                "",
                "end",
                iid=str(op_id),
                values=(
                    mark,
                    op.id,
                    op.fecha,
                    f"{op.hrs_inicio} - {op.hrs_termino}",
                    op.total_time,
                    op.nave,
                    op.servicio,
                    op.lancha,
                    f"${op.total_usd:.2f}",
                    op.proforma_smc or "-",
                ),
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
                f"Subtotal: ${totals['subtotal_usd']:,.2f} USD  |  "
                f"IVA (19%): ${totals['iva_usd']:,.2f} USD  |  "
                f"TOTAL: ${totals['total_usd']:,.2f} USD  (${totals['total_clp']:,.0f} CLP)"
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
        messagebox.showinfo(
            "Proforma Emitida Exitosamente",
            f"Folio: {folio}\nTotal: ${proforma.total_usd:,.2f} USD\n\n"
            f"Excel: {xlsx_path}\nPDF: {pdf_path}",
        )

    # =========================================================================
    # PESTAÑA 3: EMITIR ORDEN DE COMPRA (OC LANCHAS EXTERNAS)
    # =========================================================================
    def _build_tab_orden_compra(self) -> None:
        # 1. Barra superior con filtro y botón directo de emisión
        top_bar = ctk.CTkFrame(self.tab_oc)
        top_bar.pack(fill="x", side="top", padx=4, pady=4)

        ctk.CTkLabel(top_bar, text="Lancha Externa:").grid(row=0, column=0, padx=5, pady=5)
        self.oc_lancha = ctk.CTkComboBox(
            top_bar,
            width=160,
            values=["BUCA LAUREL"],
            command=lambda _v: self._search_oc_ops(),
        )
        self.oc_lancha.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(top_bar, text="Desde:").grid(row=0, column=2, padx=5, pady=5)
        self.oc_desde = ctk.CTkEntry(top_bar, width=100, placeholder_text="YYYY-MM-DD")
        self.oc_desde.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(top_bar, text="Hasta:").grid(row=0, column=4, padx=5, pady=5)
        self.oc_hasta = ctk.CTkEntry(top_bar, width=100, placeholder_text="YYYY-MM-DD")
        self.oc_hasta.grid(row=0, column=5, padx=5, pady=5)

        ctk.CTkButton(top_bar, text="Buscar Pendientes OC", width=150, command=self._search_oc_ops).grid(
            row=0, column=6, padx=6, pady=5
        )

        ctk.CTkButton(
            top_bar,
            text="Emitir Orden de Compra (Excel + PDF)",
            width=230,
            fg_color="#0F766E",
            hover_color="#115E59",
            command=self._emit_orden_compra,
        ).grid(row=0, column=7, padx=8, pady=5)

        # 2. Panel inferior fijo (empaquetado con side="bottom" ANTES de la tabla)
        bottom_panel = ctk.CTkFrame(self.tab_oc)
        bottom_panel.pack(fill="x", side="bottom", padx=4, pady=4)

        row_inputs = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row_inputs.pack(fill="x", padx=4, pady=(4, 2))

        self.oc_folio = self._labeled_entry(row_inputs, "Folio OC:", 0, 0, width=180)
        self.oc_folio.insert(0, "SMC-OC-IQQ-BL-V001")

        self.oc_fecha_em = self._labeled_entry(row_inputs, "Fecha Emisión:", 0, 2, width=105)
        self.oc_fecha_em.insert(0, date.today().isoformat())

        self.oc_proveedor = self._labeled_entry(row_inputs, "Proveedor:", 0, 4, width=260)
        self.oc_proveedor.insert(0, "Servicios Marítimos Bucalemu / Armador Externo")

        row_totals = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        row_totals.pack(fill="x", padx=8, pady=(2, 6))

        self.oc_totals_lbl = ctk.CTkLabel(
            row_totals,
            text="Subtotal OC: $0.00 USD  |  IVA (19%): $0.00 USD  |  TOTAL OC: $0.00 USD",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1B365D",
        )
        self.oc_totals_lbl.pack(side="left", padx=4)

        ctk.CTkButton(
            row_totals,
            text="Emitir Orden de Compra (Excel + PDF)",
            width=240,
            height=34,
            fg_color="#0F766E",
            command=self._emit_orden_compra,
        ).pack(side="right", padx=6)

        # 3. Tabla central de maniobras de lancha externa
        mid_frame = ctk.CTkFrame(self.tab_oc)
        mid_frame.pack(fill="both", expand=True, padx=4, pady=(0, 2))

        o_cols = ("sel", "id", "fecha", "horario", "tt", "nave", "cliente", "servicio", "lancha", "total_usd")
        self.oc_tree = ttk.Treeview(mid_frame, columns=o_cols, show="headings", height=10)
        for col, title, w in [
            ("sel", "SEL", 45),
            ("id", "ID", 45),
            ("fecha", "FECHA", 95),
            ("horario", "HORARIO", 145),
            ("tt", "TT", 75),
            ("nave", "NAVE", 155),
            ("cliente", "AGENCIA", 105),
            ("servicio", "SERVICIO", 155),
            ("lancha", "LANCHA", 115),
            ("total_usd", "TOTAL USD", 95),
        ]:
            self.oc_tree.heading(col, text=title)
            self.oc_tree.column(col, width=w)

        vsb = ttk.Scrollbar(mid_frame, orient="vertical", command=self.oc_tree.yview)
        self.oc_tree.configure(yscrollcommand=vsb.set)
        self.oc_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
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
            mark = "[✓]" if op_id in self._oc_selected_ids else "[ ]"
            self.oc_tree.insert(
                "",
                "end",
                iid=str(op_id),
                values=(
                    mark,
                    op.id,
                    op.fecha,
                    f"{op.hrs_inicio} - {op.hrs_termino}",
                    op.total_time,
                    op.nave,
                    op.cliente,
                    op.servicio,
                    op.lancha,
                    f"${op.total_usd:.2f}",
                ),
            )
        selected_ops = [self._oc_ops_map[i] for i in self._oc_selected_ids if i in self._oc_ops_map]
        totals = calculate_proforma_totals([op.total_usd for op in selected_ops])
        self.oc_totals_lbl.configure(
            text=(
                f"Subtotal OC: ${totals['subtotal_usd']:,.2f} USD  |  "
                f"IVA (19%): ${totals['iva_usd']:,.2f} USD  |  "
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
        messagebox.showinfo(
            "Orden de Compra Emitida",
            f"Folio OC: {folio_oc}\nTotal OC: ${oc.total_usd:,.2f} USD\n\n"
            f"Excel: {xlsx_path}\nPDF: {pdf_path}",
        )

    # =========================================================================
    # PESTAÑA 4: TARIFARIOS Y RESUMEN
    # =========================================================================
    def _build_tab_tarifas_resumen(self) -> None:
        self.tab_tarifas.grid_columnconfigure(0, weight=1)
        self.tab_tarifas.grid_columnconfigure(1, weight=1)
        self.tab_tarifas.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self.tab_tarifas)
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 6), pady=4)

        ctk.CTkLabel(
            left, text="Matriz de Tarifarios por Cliente (USD)", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        t_form = ctk.CTkFrame(left)
        t_form.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(t_form, text="Cliente:").grid(row=0, column=0, padx=4, pady=6)
        self.tar_cliente = ctk.CTkComboBox(t_form, width=120, values=["LBH"])
        self.tar_cliente.grid(row=0, column=1, padx=4, pady=6)

        ctk.CTkLabel(t_form, text="Servicio:").grid(row=0, column=2, padx=4, pady=6)
        self.tar_servicio = ctk.CTkComboBox(t_form, width=165, values=SERVICIOS_COMUNES)
        self.tar_servicio.grid(row=0, column=3, padx=4, pady=6)

        self.tar_valor = self._labeled_entry(t_form, "USD:", 0, 4, width=80)
        ctk.CTkButton(t_form, text="Guardar", width=85, command=self._save_tariff).grid(
            row=0, column=6, padx=6, pady=6
        )

        self.tar_tree = ttk.Treeview(left, columns=("cliente", "servicio", "valor_usd"), show="headings")
        self.tar_tree.heading("cliente", text="CLIENTE")
        self.tar_tree.heading("servicio", text="TIPO DE SERVICIO")
        self.tar_tree.heading("valor_usd", text="VALOR USD")
        self.tar_tree.column("cliente", width=110)
        self.tar_tree.column("servicio", width=220)
        self.tar_tree.column("valor_usd", width=100, anchor="e")
        self.tar_tree.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.tar_tree.bind("<<TreeviewSelect>>", self._on_tariff_select)

        right = ctk.CTkFrame(self.tab_tarifas)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 4), pady=4)

        top_r = ctk.CTkFrame(right, fg_color="transparent")
        top_r.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            top_r, text="Resumen Ejecutivo de Operaciones y Facturación", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        ctk.CTkButton(top_r, text="Actualizar", width=95, command=self._load_summary_panel).pack(side="right")

        self.summary_box = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=12))
        self.summary_box.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def _on_tariff_select(self, _event: object) -> None:
        sel = self.tar_tree.selection()
        if not sel:
            return
        vals = self.tar_tree.item(sel[0], "values")
        if vals:
            self.tar_cliente.set(vals[0])
            self.tar_servicio.set(vals[1])
            self.tar_valor.delete(0, "end")
            self.tar_valor.insert(0, vals[2])

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
        for t in self.db.list_tariffs():
            self.tar_tree.insert("", "end", values=(t.codigo_agencia, t.servicio, f"{t.valor_usd:.2f}"))

    def _load_summary_panel(self) -> None:
        summary = self.db.get_operations_summary()
        lines: list[str] = []

        lines.append("=== RESUMEN POR CLIENTE / AGENCIA ===")
        lines.append(f"{'CLIENTE':<18} {'MANIOBRAS':>10} {'TOTAL USD':>16}")
        lines.append("-" * 46)
        total_ops = 0
        total_usd = 0.0
        for row in summary["por_cliente"]:
            qty = int(row["cantidad"] or 0)
            usd = float(row["total_usd"] or 0.0)
            total_ops += qty
            total_usd += usd
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

        self._load_operations_table()
        self._load_tariffs_table()
        self._load_summary_panel()


def main() -> None:
    """Punto de entrada de la interfaz gráfica."""
    app = SMCOperacionesApp()
    app.mainloop()


if __name__ == "__main__":
    main()

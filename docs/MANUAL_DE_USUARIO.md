# 📘 Manual de Usuario y Catálogo de Funcionalidades — SMC Operaciones

**Sistema:** Control de Operaciones, Proformas de Servicio y Órdenes de Compra  
**Empresa:** Servicios Marítimos Carrere (SMC) — Operaciones Iquique  
**Versión:** 1.0 (MVP)  

---

## 1. ¿Qué puede hacer esta aplicación? (Catálogo Completo de Capacidades)

El sistema **SMC Operaciones** digitaliza y automatiza el flujo completo entre las maniobras realizadas en el puerto y la facturación/liquidación comercial:

1. **Bitácora Digital de Operaciones (18 Columnas Oficiales):**
   - Importa automáticamente las maniobras históricas desde `Control de Operaciones Iquique.xlsx` descartando filas vacías con fórmulas en cero.
   - Registra, edita y elimina maniobras portuarias manteniendo las 18 columnas exactas de SMC.
2. **Cálculo Automático de Horarios (`TOTAL TIME`) con Cruce de Medianoche:**
   - Calcula al instante la duración de cada servicio ($\text{Hrs Término} - \text{Hrs Inicio}$).
   - Si una maniobra nocturna inicia antes de las `00:00` (ej. `23:30:00`) y termina al día siguiente (ej. `00:45:00`), suma automáticamente 24 horas entregando `01:15:00` sin errores negativos.
3. **Motor Inteligente de Tarifarios por Cliente:**
   - Incluye precargados los tarifarios únicos en USD de **LBH**, **CPT BOATS**, **IAN TAYLOR**, **BUCALEMU** y **LORENA IQQ**.
   - Al elegir `Cliente` + `Servicio`, autocompleta el precio base en USD y suma cualquier recargo (`Extra USD`) en tiempo real.
4. **Emisión Automática de Proformas de Servicio (Excel + PDF):**
   - Filtra las maniobras por **Agencia Cliente** y **Nave** (ej. *SHUN XING 17*), evitando que se mezclen filas de otros buques.
   - Calcula Subtotal USD, IVA ($19\%$), Total USD y la conversión referencial a Pesos Chilenos según el Dólar Observado.
   - Genera simultáneamente el archivo `.xlsx` y el documento `.pdf` con membrete corporativo SMC (`RUT 77.000.970-7`).
5. **Prevención Automática de Doble Facturación:**
   - Al emitir una Proforma, todas las maniobras incluidas quedan marcadas con su folio (ej. `SMC-PDS-IQQ-LBH-V6526`) y cambian a estado `AGENCIA`.
   - Si alguien intenta cobrar nuevamente una maniobra ya facturada, el sistema muestra una alerta de seguridad.
6. **Emisión de Órdenes de Compra (OC) para Lanchas Subcontratadas:**
   - Detecta automáticamente las maniobras ejecutadas por embarcaciones arrendadas a terceros (como la lancha **`BUCA LAUREL`**).
   - Agrupa los servicios pendientes de pago al armador externo y emite la Orden de Compra en formato `.xlsx` y `.pdf`.
7. **Dashboard de KPIs y Estadísticas en Tiempo Real:**
   - Muestra en la franja superior el total de maniobras, facturación acumulada en USD, servicios pendientes de Proforma y maniobras pendientes de OC.

---

## 2. Guía de Uso Paso a Paso por Módulo

### 🧭 Navegación General
En el **menú lateral izquierdo (oscuro)** encontrarás los 4 módulos principales y 3 botones de acceso rápido en la parte inferior:
- **📂 Abrir Carpeta Exportados:** Abre directamente la carpeta `data/export/` donde se guardan todas las Proformas y Órdenes de Compra en PDF y Excel.
- **📥 Importar Planilla Excel:** Permite cargar una planilla `.xlsx` de Control de Operaciones.
- **🖥️ Pantalla Completa (F11):** Activa o desactiva el modo pantalla completa.

---

### Módulo 1: 📋 Control de Operaciones (Bitácora Diaria)

#### ¿Cómo buscar o filtrar maniobras?
- Escribe cualquier parte del nombre del buque en **`🔍 Buscar Nave:`** y la tabla se filtrará instantáneamente mientras escribes.
- También puedes combinar filtros por rango de fechas (`Desde` / `Hasta`), `Cliente`, `Lancha` (`DOÑA RENATA` o `BUCA LAUREL`) y `Estado` (`PENDIENTE`, `AGENCIA`, `FACTURA`, `INTERNO`).
- Los registros en la tabla se colorean automáticamente según su estado:
  - 🟢 **Verde (`FACTURA`):** Servicio facturado.
  - 🔵 **Azul (`AGENCIA`):** Servicio con Proforma enviada a la agencia.
  - 🟡 **Ámbar (`PENDIENTE`):** Maniobra pendiente de liquidar.

#### ¿Cómo registrar una nueva maniobra?
1. En el formulario superior, verifica la **Fecha**, **Inicio** (`HH:MM:SS`) y **Término** (`HH:MM:SS`). Verás que el campo **`⏱️ TT`** se calcula solo.
2. Escribe el nombre de la **Nave**, selecciona el **Cliente** y el **Servicio**: el campo **`Valor USD`** se rellenará automáticamente con la tarifa oficial de ese cliente.
3. Si hubo recargo por sobretiempo, ingrésalo en **`Extra USD`** y verifica el **`💵 Total USD`**.
4. Haz clic en el botón verde **`➕ Guardar Nueva Maniobra`**.

#### ¿Cómo editar o eliminar una maniobra existente?
1. Haz clic sobre cualquier fila de la tabla inferior: sus datos se cargarán en el formulario superior.
2. Modifica los datos necesarios y presiona **`💾 Actualizar Seleccionada`** (o **`🗑️ Eliminar`** si deseas borrarla).

---

### Módulo 2: 📄 Proformas de Servicio (Liquidación a Clientes)

Este módulo está diseñado en **3 pasos visuales** para emitir una pre-factura en menos de 10 segundos:

1. **PASO 1 (Elegir Cliente y Nave):**
   - Selecciona la **Agencia** (ej. `LBH`).
   - En el desplegable **Nave Atendida**, elige el buque (ej. `SHUN XING 17`). La tabla cargará automáticamente todas las maniobras de esa nave.
2. **PASO 2 (Seleccionar Maniobras):**
   - Revisa la tabla central. Las maniobras marcadas con **`[✓] Sí`** (en color verde suave) se incluirán en la Proforma.
   - Haz clic sobre cualquier fila si deseas desmarcarla (`[ ] No`) o volver a marcarla.
3. **PASO 3 (Verificar Folio, Dólar y Emitir):**
   - En la barra inferior, verifica el **Folio Proforma** (ej. `SMC-PDS-IQQ-LBH-V6526`), la **Clasificación** (`F/V` o `M/N`) y el **Dólar Obs. (CLP)** (ej. `981.08`).
   - Revisa en vivo el **Subtotal USD**, **IVA (19%)** y **TOTAL USD**.
   - Haz clic en **`🚀 Emitir Proforma (Excel + PDF)`**. El sistema creará ambos archivos en `data/export/` y te preguntará si deseas abrir la carpeta para revisarlos o enviarlos por correo.

---

### Módulo 3: 🚤 Órdenes de Compra (Pago a Lanchas Arrendadas)

Cuando SMC utiliza una lancha externa (como **`BUCA LAUREL`**), este módulo permite generar la Orden de Compra para pagarle al dueño de la embarcación:

1. **PASO 1:** Selecciona la **Lancha Subcontratada** (`BUCA LAUREL`) y opcionalmente el rango de fechas (ej. `2026-10-21`).
2. **PASO 2:** Revisa en la tabla las maniobras ejecutadas por esa lancha que están pendientes de Orden de Compra (puedes marcar o desmarcar filas con un clic).
3. **PASO 3:** Verifica el **Folio OC** (ej. `SMC-OC-IQQ-BL-V001`), el nombre del **Proveedor / Armador** y presiona **`🚀 Emitir Orden de Compra (Excel + PDF)`**.

---

### Módulo 4: 📊 Tarifarios y Dashboard

- **Panel Izquierdo (Catálogo de Tarifarios USD):** Haz clic sobre cualquier tarifa de la tabla para editar su precio en dólares, o selecciona un `Cliente` y `Servicio`, escribe el nuevo monto en `USD` y presiona **`💾 Guardar`**.
- **Panel Derecho (Distribución Comercial):** Visualiza mediante barras de progreso qué porcentaje de la facturación corresponde a cada agencia naviera y el desglose completo por lancha y tipo de servicio.
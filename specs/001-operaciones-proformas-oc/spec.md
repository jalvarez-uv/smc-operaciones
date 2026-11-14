# Feature Specification: SMC Operaciones - Control de Operaciones, Proformas de Servicio y Órdenes de Compra

**Feature Branch**: `001-operaciones-proformas-oc`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Lee íntegramente los archivos docs/SRS.md y docs/PLAN_DE_PRUEBAS.md y genera la especificación funcional completa del sistema SMC-Operaciones para los 3 apartados solicitados por la empresa: 1. Control de Operaciones: Gestión CRUD, filtros por Fecha/Nave/Cliente/Lancha/Estado, cálculo automático de TOTAL TIME (HRS TERMINO - HRS INICIO con soporte de cruce de medianoche) y TOTAL USD (VALOR USD + EXTRA USD), más importación y exportación compatible con Control de Operaciones Iquique.xlsx. 2. Proforma de Servicios (Orden de Servicio al Cliente): Pre-factura comercial agrupada por Cliente y Nave con tarifario único por cliente (LBH, CPT BOATS, IAN TAYLOR, BUCALEMU, LORENA IQQ), cálculo de Subtotal USD, IVA 19%, Total USD, referencia de Valor Dólar, exportación a Excel (.xlsx) y PDF corporativo, y marcado automático del folio PROFORMA SMC en las operaciones para evitar doble cobro. 3. Órdenes de Compra (OC a Proveedores de Lanchas): Liquidación de pagos cuando una lancha externa/arrendada (como BUCA LAUREL) presta servicios a SMC, filtrando dichas maniobras y generando el documento OC en Excel (.xlsx) y PDF."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Control Integral de Maniobras y Bitácora Operativa (Priority: P1)

Como operador marítimo y administrador de SMC, necesito registrar, editar, consultar, filtrar e importar/exportar las maniobras de lanchaje en bahía de manera ágil y segura, de modo que la bitácora operativa mantenga el cálculo exacto de tiempos y montos, reflejando fielmente la estructura estándar de 18 columnas de la empresa.

**Why this priority**: Es la columna vertebral del negocio operativo. Sin un registro fidedigno de maniobras con duraciones y montos en USD correctamente calculados, resulta imposible facturar a los clientes o liquidar a los proveedores de lanchas.

**Independent Test**: Puede ser probado de forma independiente registrando maniobras manuales (diurnas y con cruce de medianoche), importando la planilla histórica `Control de Operaciones Iquique.xlsx` (476 operaciones) y verificando el cálculo automático de `TOTAL TIME`, `TOTAL USD` y la persistencia de los 18 campos.

**Acceptance Scenarios**:

1. **Given** una maniobra diurna con inicio `09:15:00` y término `09:45:00`, **When** el usuario ingresa los horarios, **Then** el sistema calcula y asigna automáticamente `TOTAL TIME` = `00:30:00` (30 minutos).
2. **Given** una maniobra nocturna que cruza la medianoche con inicio `23:30:00` y término `00:45:00` del día siguiente, **When** el usuario registra los horarios, **Then** el sistema calcula automáticamente `TOTAL TIME` = `01:15:00` (75 minutos), sin generar duraciones negativas ni errores de desbordamiento de 24 horas.
3. **Given** una maniobra con `VALOR USD` = `330.00` y un recargo `EXTRA USD` = `330.00`, **When** se registran o actualizan los valores, **Then** el sistema calcula automáticamente `TOTAL USD` = `660.00`.
4. **Given** la planilla real `Control de Operaciones Iquique.xlsx`, **When** el usuario solicita la importación, **Then** el sistema procesa las 476 operaciones válidas respetando las 18 columnas estándar e ignora las filas vacías que solo contienen fórmulas en cero.
5. **Given** la bitácora con múltiples registros, **When** el usuario aplica filtros por Fecha, Nave, Cliente, Lancha o Estado, **Then** el sistema actualiza la vista mostrando únicamente las maniobras que coinciden con los criterios seleccionados.

---

### User Story 2 - Liquidación Comercial y Emisión de Proformas de Servicio por Cliente y Nave (Priority: P2)

Como administrador comercial de SMC, necesito seleccionar maniobras realizadas para una nave y cliente específicos, autocompletar sus tarifas en USD, calcular Subtotal, IVA (19%) y Total USD, e imprimir/exportar la Proforma de Servicios en formatos Excel y PDF oficial, asegurando que cada operación quede marcada con su folio comercial para prevenir dobles cobros.

**Why this priority**: Representa el proceso de facturación y cobro a las agencias navieras (ingresos de la empresa). Automatizar este proceso elimina horas de confección manual y errores de copiado y pegado entre planillas.

**Independent Test**: Puede ser probado seleccionando las 5 maniobras de la nave testigo *SHUN XING 17* del cliente *LBH* (fecha 29/10/2026), verificando el autocompletado tarifario, el cálculo de Subtotal = $2.030,00 USD, IVA 19% = $385,70 USD, Total = $2.415,70 USD, la generación de documentos (.xlsx y .pdf) y la actualización automática del campo `PROFORMA SMC` con el folio `SMC-PDS-IQQ-LBH-V6526`.

**Acceptance Scenarios**:

1. **Given** que el usuario selecciona al cliente `LBH` y el servicio `RECEPCIÓN`, **When** se solicita la tarifa base sugerida, **Then** el sistema autocompleta el monto sugerido de `650.00 USD`.
2. **Given** un conjunto de maniobras ejecutadas para la nave `SHUN XING 17` de la agencia `LBH`, **When** el usuario genera la Proforma con Folio `SMC-PDS-IQQ-LBH-V6526` y Tipo de Cambio `$981,08 CLP/USD`, **Then** el sistema produce el documento comercial desglosando fecha, horario `DD/MM/YYYY HH:MM:SS a HH:MM:SS TT: H:MM:SS`, Subtotal (`2030.00 USD`), IVA 19% (`385.70 USD`), Total (`2415.70 USD`) y valor en moneda local.
3. **Given** una Proforma generada y confirmada, **When** el documento es emitido, **Then** todas las maniobras incluidas actualizan automáticamente su campo `PROFORMA SMC` con el folio emitido y su `ESTADO` pasa a `AGENCIA` o `FACTURA`.
4. **Given** un conjunto de operaciones que ya tienen asignado un folio de `PROFORMA SMC`, **When** un usuario intenta incluirlas en una nueva Proforma, **Then** el sistema previene la acción emitiendo una advertencia explícita de duplicidad comercial.
5. **Given** la solicitud de emisión de Proforma, **When** el usuario presiona exportar, **Then** el sistema genera tanto el archivo Excel (.xlsx) con fórmulas matemáticas vivas como el archivo PDF corporativo con membrete oficial en menos de 3 segundos.

---

### User Story 3 - Liquidación de Costos y Emisión de Órdenes de Compra para Lanchas Subcontratadas (Priority: P3)

Como administrador operativo de SMC, necesito identificar rápidamente las maniobras ejecutadas por embarcaciones arrendadas a terceros (como la lancha `BUCA LAUREL`), agruparlas por proveedor y período, y emitir la Orden de Compra oficial de SMC en formatos Excel y PDF para autorizar el pago a dicho armador externo.

**Why this priority**: Resuelve el control de costos operativos y la relación contractual con proveedores clave. Permite saldar los servicios de lanchas subcontratadas con respaldo documental fidedigno.

**Independent Test**: Puede ser probado filtrando las operaciones ejecutadas por la lancha externa `BUCA LAUREL` para la fecha `21/10/2026`, verificando la inclusión exacta de las 6 maniobras correspondientes a las naves `RONG HENG 68` y `HUA YING 66`, la exclusión de maniobras de la lancha propia `DOÑA RENATA`, y la emisión de la Orden de Compra foliada en Excel y PDF.

**Acceptance Scenarios**:

1. **Given** una bitácora con maniobras de lanchas propias (`DOÑA RENATA`) y subcontratadas (`BUCA LAUREL`), **When** el usuario ingresa al módulo de Órdenes de Compra y selecciona `BUCA LAUREL`, **Then** el sistema lista únicamente las operaciones realizadas por dicha embarcación externa que se encuentren pendientes de liquidación.
2. **Given** las 6 maniobras del 21/10/2026 ejecutadas por `BUCA LAUREL`, **When** el usuario emite la Orden de Compra con folio `SMC-OC-IQQ-...`, **Then** el sistema consolida las líneas de costo acordadas con el proveedor y genera los documentos `.xlsx` y `.pdf`.
3. **Given** una Orden de Compra emitida, **When** el documento se confirma, **Then** las operaciones asociadas registran su estado de liquidación de compra para evitar dobles pagos a proveedores.

---

### User Story 4 - Visualización y Resumen de Servicios y Facturación (Priority: P4)

Como administrador general de SMC, necesito consultar métricas agregadas de maniobras realizadas por cliente, tipo de servicio, lancha y montos totales en USD, de modo que pueda monitorear la carga operativa y comercial sin necesidad de crear tablas dinámicas manuales en Excel.

**Why this priority**: Proporciona visibilidad ejecutiva sobre el volumen de negocio y el rendimiento operativo de la flota propia vs. flota arrendada.

**Independent Test**: Puede ser probado consultando la pantalla de métricas o resumen y comparando los totales de servicios por cliente y por tipo de maniobra contra la hoja resumen `GRAFICO X SERVICIOS` de la planilla original.

**Acceptance Scenarios**:

1. **Given** un conjunto de operaciones en un rango de fechas, **When** el usuario visualiza el resumen ejecutivo, **Then** el sistema presenta el conteo de maniobras por cliente (`LBH`, `CPT BOATS`, etc.) y por tipo de servicio (`RECEPCIÓN`, `REGIMEN UP`, `REGIMEN OUT`, `SHIPCHANDLER`, etc.).
2. **Given** la consulta de resumen, **When** se analizan las lanchas, **Then** el sistema desglosa la cantidad de servicios y horas navegadas entre la lancha propia `DOÑA RENATA` y lanchas externas como `BUCA LAUREL`.

---

### Edge Cases

- **Cruce de Medianoche en Horario de Maniobra**: Cuando una maniobra inicia antes de la medianoche (ej. `23:30:00`) y culmina en la madrugada del día calendario siguiente (ej. `00:45:00`), el sistema debe sumar 24 horas a la hora de término de forma automática para calcular `01:15:00`, impidiendo diferencias negativas o valores en error (`######` o valores superiores a 24 horas no justificados).
- **Filas Vacías con Fórmulas en Cero en la Planilla Base**: Durante la importación de `Control de Operaciones Iquique.xlsx`, el sistema debe omitir filas no operativas que contienen únicamente valores precalculados en cero (`00:00:00` o `$0`), importando exactamente los 476 registros de maniobras legítimas.
- **Doble Asignación de Proforma**: Si un usuario intenta generar una Proforma incluyendo maniobras que ya cuentan con un folio `PROFORMA SMC` asignado, el sistema debe alertar al usuario y bloquear la generación a menos que se solicite explícitamente una re-emisión o desvinculación autorizada.
- **Operaciones de Lancha Externa para Múltiples Naves en un Mismo Día**: Una lancha externa como `BUCA LAUREL` puede ejecutar maniobras para varias naves (ej. *RONG HENG 68* y *HUA YING 66*) en una sola jornada; la Orden de Compra al proveedor debe agrupar todas las maniobras de dicha lancha para el proveedor, independientemente de que las naves pertenezcan a clientes navieros distintos.
- **Recargos y Descuentos Manuales**: Cuando una maniobra amerita un recargo por sobretiempo o espera prolongada, el usuario puede registrar un monto en `EXTRA USD` (positivo) o descuento (`Dcto` / negativo); el sistema debe recalcular inmediatamente `TOTAL USD` y reflejar el ajuste en la línea de la Proforma.
- **Valores Nulos o Faltantes en Datos Opcionales**: Maniobras que no cuenten de inmediato con `OC CTE`, `FACTURA SMC`, `LBH AGENCIAMIENTO` u `OBSERVACIONES` deben guardarse sin errores de validación, admitiendo su completado posterior.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir registrar, modificar, consultar y eliminar operaciones marítimas, manteniendo la estructura de 18 columnas estándar: `FECHA`, `HRS INICIO`, `HRS TERMINO`, `TOTAL TIME`, `NAVE`, `CLIENTE`, `SERVICIO`, `TERMINAL`, `LANCHA`, `VALOR USD`, `EXTRA USD`, `TOTAL USD`, `OBSERVACIONES`, `ESTADO`, `PROFORMA SMC`, `OC CTE`, `FACTURA SMC` y `LBH AGENCIAMIENTO`.
- **FR-002**: El sistema DEBE calcular automáticamente `TOTAL TIME` a partir de `HRS INICIO` y `HRS TERMINO`. Si la hora de término es inferior a la de inicio, el sistema DEBE asumir que la maniobra cruzó la medianoche sumando 24 horas al cálculo para arrojar un resultado positivo en formato `HH:MM:SS`.
- **FR-003**: El sistema DEBE calcular automáticamente `TOTAL USD` como la suma aritmética de `VALOR USD` y `EXTRA USD` para cada operación registrada.
- **FR-004**: El sistema DEBE proveer filtros de búsqueda combinables por Rango de Fechas, Nombre de Nave, Agencia/Cliente, Lancha asignada, Tipo de Servicio y Estado operativo/comercial (`PENDIENTE`, `AGENCIA`, `FACTURA`, `INTERNO`).
- **FR-005**: El sistema DEBE importar datos históricos desde archivos de hoja de cálculo con formato idéntico a `Control de Operaciones Iquique.xlsx`, validando tipos de datos y descartando filas vacías con fórmulas en cero.
- **FR-006**: El sistema DEBE permitir exportar la bitácora completa o los registros filtrados a una hoja de cálculo compatible con el formato histórico de SMC.
- **FR-007**: El sistema DEBE administrar un catálogo de clientes y agencias marítimas (`LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`), incluyendo datos de contacto comercial (Nombre de Contacto, Correo Electrónico, Teléfono).
- **FR-008**: El sistema DEBE mantener una matriz tarifaria configurable con el valor base en USD por cada combinación de Cliente y Tipo de Servicio (ej. `LBH - RECEPCIÓN: 650.00 USD`, `CPT BOATS - RECEPCIÓN: 350.00 USD`).
- **FR-009**: Al registrar una nueva operación o editar el servicio de una maniobra, el sistema DEBE sugerir y autocompletar el `VALOR USD` correspondiente según la matriz tarifaria del cliente seleccionado, permitiendo modificación manual justificada.
- **FR-010**: El sistema DEBE administrar el catálogo de lanchas portuarias, diferenciando lanchas de flota propia (ej. `DOÑA RENATA`) de lanchas de proveedores externos o arrendadas (ej. `BUCA LAUREL`).
- **FR-011**: El sistema DEBE permitir generar Proformas de Servicio seleccionando un Cliente y una Nave receptora del servicio, listando todas las maniobras elegibles no liquidadas.
- **FR-012**: La Proforma de Servicios DEBE calcular y presentar:
  - Subtotal USD (suma de importes de maniobras desglosadas).
  - Tasa de IVA aplicable ($19\%$).
  - Monto de IVA USD ($\text{Subtotal USD} \times 0.19$).
  - Total Proforma USD ($\text{Subtotal USD} + \text{IVA USD}$).
  - Referencia de Valor Dólar Observado (CLP) y total aproximado en moneda local.
- **FR-013**: Cada Proforma DEBE recibir un código de folio comercial identificador único (ej. `SMC-PDS-IQQ-[CLIENTE]-V[XXXX]`).
- **FR-014**: Al emitir o confirmar una Proforma, el sistema DEBE actualizar automáticamente el campo `PROFORMA SMC` de todas las maniobras incluidas con el folio generado, y cambiar su `ESTADO` a `AGENCIA` o `FACTURA`.
- **FR-015**: El sistema DEBE bloquear o advertir la inclusión de maniobras que ya cuenten con un folio `PROFORMA SMC` en una nueva proforma, previniendo dobles cobros.
- **FR-016**: El sistema DEBE exportar la Proforma de Servicios en formato de hoja de cálculo editable (.xlsx) preservando la plantilla corporativa, celdas de encabezado de cliente/nave y fórmulas aritméticas vivas.
- **FR-017**: El sistema DEBE generar la Proforma de Servicios en formato PDF corporativo oficial, listo para envío digital, con diagramación profesional, membrete de SMC y firmas/condiciones de servicio.
- **FR-018**: El sistema DEBE identificar de forma autónoma las operaciones ejecutadas por lanchas subcontratadas/externas y disponibilizarlas en un módulo de liquidación de compras a proveedores.
- **FR-019**: El sistema DEBE permitir generar Órdenes de Compra a proveedores externos de lanchas, agrupando maniobras por Lancha y rango de fechas, con asignación de folio único de compra y cálculo de subtotal y totales correspondientes.
- **FR-020**: El sistema DEBE exportar las Órdenes de Compra a formatos Excel (.xlsx) y PDF corporativo, actualizando la trazabilidad de liquidación de costos de dichas maniobras.

---

### Key Entities *(include if feature involves data)*

- **Operacion (Maniobra Portuaria)**: Registro atómico de un servicio de lanchaje prestado en la bahía o terminal. Posee fecha, hora inicio, hora término, duración calculada (`TOTAL TIME`), nave atendida, cliente contratante, tipo de servicio, terminal portuario de atraque/zarpe, lancha ejecutora, valor base en USD, valor extra en USD, monto total en USD, observaciones, estado operativo/financiero y los folios vinculados de trazabilidad (`PROFORMA SMC`, `OC CTE`, `FACTURA SMC`, `LBH AGENCIAMIENTO`).
- **Cliente (Agencia Naviera)**: Entidad comercial contratante del servicio de apoyo marítimo (ej. `LBH`, `CPT BOATS`, `IAN TAYLOR`, `BUCALEMU`, `LORENA IQQ`). Incluye código de agencia, persona de contacto, dirección de correo electrónico y teléfono.
- **TarifaCliente**: Matriz de valorización comercial que define el precio estándar en USD asignado a cada tipo de servicio para un cliente específico.
- **Lancha**: Embarcación que ejecuta materialmente el servicio en el agua. Posee nombre y clasificación de propiedad (Propia de SMC, como `DOÑA RENATA`, o Externa/Subcontratada, como `BUCA LAUREL`).
- **ProveedorLancha**: Persona natural o jurídica propietaria de embarcaciones menores arrendadas o subcontratadas por SMC para complementar la capacidad de su flota.
- **ProformaServicio**: Documento comercial de cobro (pre-factura) emitido por SMC a una agencia naviera por los servicios prestados a una nave en una fecha o recalada. Contiene folio único, fecha de emisión, cliente, datos de la nave, valor de cambio dólar observado, lista de maniobras detalladas, Subtotal USD, IVA 19% y Total USD.
- **OrdenCompra**: Documento de liquidación de costos emitido por SMC hacia el proveedor de una lancha externa por los servicios subcontratados. Contiene folio único, fecha de emisión, proveedor, lancha, relación de maniobras y montos a liquidar.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los cálculos de duración de maniobra (`TOTAL TIME`) con cruce de medianoche se resuelven con exactitud matemática positiva en formato `HH:MM:SS` (ej. de 23:30 a 00:45 resulta en 01:15:00).
- **SC-002**: La importación de las 476 operaciones de la planilla real `Control de Operaciones Iquique.xlsx` se completa de forma íntegra sin omitir ninguna de las 18 columnas estándar ni incorporar filas en cero generadas por fórmulas de Excel vacías.
- **SC-003**: El tiempo total de procesamiento y exportación de documentos (Proforma u Orden de Compra en Excel o PDF) es inferior a 3 segundos por documento.
- **SC-004**: Tasa de duplicidad de facturación del 0%: ninguna operación con folio de proforma asignado puede ser incorporada a un nuevo documento sin previo desbloqueo explícito del usuario.
- **SC-005**: Cuadre financiero del 100% en la Proforma testigo de la nave *SHUN XING 17*: Subtotal de exactamente `$2.030,00 USD`, IVA 19% de `$385,70 USD` y Total de `$2.415,70 USD`.
- **SC-006**: Filtrado y liquidación exacta del 100% de maniobras ejecutadas por lanchas subcontratadas (validación testigo de 6 operaciones para la lancha *BUCA LAUREL* del 21/10/2026).
- **SC-007**: Los usuarios pueden filtrar y localizar cualquier maniobra histórica por cliente, nave o rango de fechas en menos de 2 segundos.

---

## Assumptions

- **Régimen Tributario**: Todos los servicios marítimos prestados a agencias navieras nacionales se encuentran afectos al Impuesto al Valor Agregado (IVA) del 19% chileno, calculado sobre el Subtotal neto en USD.
- **Moneda Base y Tipo de Cambio**: La moneda de valorización contractual y bitácora es el dólar estadounidense (USD). La referencia en pesos chilenos (CLP) calculada en la Proforma es meramente informativa según el tipo de cambio "Dólar Observado" provisto para la fecha de emisión.
- **Modalidad Operativa Local**: El sistema operará con almacenamiento de datos local y autocontenido para el puesto de trabajo del operador en Iquique, asegurando funcionamiento continuo independientemente de la conectividad a Internet.
- **Formato Documental Oficial**: Las plantillas corporativas generadas en Excel deben mantener exactamente la diagramación, celdas de observaciones y fórmulas aritméticas de las plantillas originales aprobadas por la gerencia de SMC.
- **Unicidad de Folio**: Los folios de Proforma siguen la convención corporativa `SMC-PDS-IQQ-[CLIENTE]-V[XXXX]` y son gestionados correlativamente por el operador comercial.


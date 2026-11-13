# Plan de Pruebas de Software (QA & Testing)
**Proyecto:** SMC-Operaciones  
**Organización:** Servicios Marítimos Carrere (SMC)  
**Responsable:** Jorge Eduardo Álvarez Alarcón  
**Herramienta de Automatización:** `pytest`  

---

## 1. Estrategia de Pruebas
El plan de pruebas se estructura en tres niveles de validación para garantizar cero errores aritméticos, de horarios o de cruce de naves antes de la entrega final del MVP el 27 de noviembre de 2026:

1. **Pruebas Unitarias (`tests/test_calculator.py`):** Verificación matemática aislada del cálculo de duración de maniobras (`TOTAL TIME`), cruce de medianoche, aplicación de tarifarios por cliente, recargos (`EXTRA USD`), descuentos y cálculo de IVA ($19\%$).
2. **Pruebas de Integración (`tests/test_excel_import_export.py`):** Verificación de lectura íntegra del archivo real `Control de Operaciones Iquique.xlsx` (476 maniobras), persistencia en SQLite y generación de archivos `.xlsx` y `.pdf`.
3. **Pruebas de Aceptación de Usuario (Casos Reales SMC):** Validación de extremo a extremo comparando los documentos generados por el sistema contra las Proformas de Servicio reales emitidas por la empresa.

---

## 2. Matriz de Casos de Prueba

| ID | Nivel | Caso de Prueba | Datos de Entrada | Resultado Esperado |
| :--- | :--- | :--- | :--- | :--- |
| **CP-01** | Unitaria | Cálculo de `TOTAL TIME` en horario diurno | `HRS INICIO: 09:15:00`, `HRS TERMINO: 09:45:00` | `TOTAL TIME: 00:30:00` ($30\text{ min}$) |
| **CP-02** | Unitaria | Cálculo de `TOTAL TIME` con cruce de medianoche | `HRS INICIO: 23:30:00`, `HRS TERMINO: 00:45:00` | `TOTAL TIME: 01:15:00` ($75\text{ min}$, sin valores negativos) |
| **CP-03** | Unitaria | Cálculo de `TOTAL USD` con recargo extra | `VALOR USD: 330.00`, `EXTRA USD: 330.00` (Caso real fila 8 *LU PENG YUAN YU 089*) | `TOTAL USD: 660.00` |
| **CP-04** | Unitaria | Autocompletado de Tarifario Cliente `LBH` | `CLIENTE: LBH`, `SERVICIO: RECEPCIÓN` | `VALOR USD sugerido: 650.00` |
| **CP-05** | Unitaria | Autocompletado de Tarifario Cliente `CPT BOATS` | `CLIENTE: CPT BOATS`, `SERVICIO: RECEPCIÓN` | `VALOR USD sugerido: 350.00` |
| **CP-06** | Aceptación | Generación de Proforma Real *SHUN XING 17* | Cliente `LBH`, Nave `SHUN XING 17`, Fecha `29/10/2026` (5 maniobras: 1 Recepción $\$650$, 2 Regimen Up $\$350$, 1 Regimen Out $\$350$, 1 Shipchandler $\$330$) | Subtotal = $2030.00\text{ USD}$, IVA ($19\%$) = $385.70\text{ USD}$, Total = $2415.70\text{ USD}$ ($\$2.416\text{ USD}$ redondeado), con 5 filas exactas sin datos residuales de otras naves |
| **CP-07** | Aceptación | Generación de Orden de Compra Lancha Externa *BUCA LAUREL* | Lancha `BUCA LAUREL`, Fecha `21/10/2026` | Filtra exactamente las 6 maniobras de las naves `RONG HENG 68` y `HUA YING 66` y genera la Orden de Compra al proveedor sin incluir maniobras de `DOÑA RENATA` |
| **CP-08** | Integración | Importación íntegra de Planilla Base | Archivo `Control de Operaciones Iquique.xlsx` | Importa las 476 operaciones válidas e ignora las filas vacías al final de la hoja que solo contienen fórmulas en cero (`00:00:00` / `$0`) |
| **CP-09** | Integración | Prevención de doble facturación | Intentar emitir una segunda Proforma para las mismas 5 maniobras de `SHUN XING 17` ya marcadas con folio `SMC-PDS-IQQ-LBH-V6526` | El sistema muestra advertencia indicando que las maniobras ya poseen Proforma asignada |

---

## 3. Criterios de Aceptación para Entrega del MVP (27 de Noviembre)
1. **100% de pruebas unitarias aprobadas** al ejecutar `pytest -v` tanto en Linux Mint como en el flujo de integración continua de GitHub Actions (`windows-latest`).
2. **Validación de Proforma Testigo:** El archivo PDF y Excel generado para la nave *SHUN XING 17* (Folio `SMC-PDS-IQQ-LBH-V6526`) debe coincidir exactamente en montos y horarios con el documento oficial de referencia de SMC.
3. **Validación de Orden de Compra Testigo:** Emisión exitosa de la Orden de Compra para las 6 operaciones de la lancha `BUCA LAUREL` del 21/10/2026.
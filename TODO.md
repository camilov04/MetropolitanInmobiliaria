# TODO - Modificaciones Sistema Inmobiliario

## FASE 1: Estados de Inmuebles (Disponible/Pendiente/No Disponible)
- [x] 1.1 Modificar modelo Inmueble: cambiar estado a ENUM con valores disponible/pendiente/no_disponible
- [x] 1.2 Agregar campo estado_detalle para especificar sub-estado de pendiente
- [x] 1.3 Crear migración Alembic para nuevos campos
- [x] 1.4 Actualizar admin_inmuebles.html: reemplazar botón "Arrendar" por select de estado
- [x] 1.5 Crear endpoint AJAX para cambio rápido de estado
- [x] 1.6 Actualizar filtros en catálogo público: solo mostrar "disponible"
- [x] 1.7 Actualizar admin_inmuebles para mostrar/ocultar según estado
- [x] 1.8 Actualizar dashboard metrics con nuevos estados

## FASE 2: Menú Hamburguesa Deslizable
- [x] 2.1 Modificar base_admin.html: agregar botón hamburguesa y menú lateral
- [x] 2.2 Crear CSS para menú deslizable derecha→izquierda
- [x] 2.3 Migrar botones actuales al menú lateral
- [x] 2.4 Destacar botón "Agregar inmueble" en el menú
- [x] 2.5 Agregar botones placeholder para Facturación y Estadísticas

## FASE 3: Módulo de Facturación
- [x] 3.1 Crear modelos: ContratoArriendo, PagoArriendo, Ingreso, OtroIngreso, Gasto
- [x] 3.2 Crear migración para tablas de facturación
- [x] 3.3 Crear template facturacion.html con búsqueda de inmuebles
- [x] 3.4 Crear template detalle_facturacion.html (editable + datos de facturación)
- [x] 3.5 Crear rutas: /admin/facturacion, /admin/facturacion/<id>
- [x] 3.6 Implementar lógica de cálculo de mora y estados de pago
- [x] 3.7 Agregar filtros de búsqueda (nombre, ID, dirección)

## FASE 4: Módulo de Estadísticas
- [x] 4.1 Crear template estadisticas.html
- [x] 4.2 Integrar Chart.js para gráficas
- [x] 4.3 Gráfica circular: estados de pagos (pagado/pendiente/vencido) por mes
- [x] 4.4 Gráfica barras: valor total recaudado por mes y año
- [x] 4.5 Gráfica barras: días en mora por inquilino (mes)
- [x] 4.6 Gráfica comparación: ingresos vs gastos (mes y año)
- [x] 4.7 Gráfica circular: gastos por porcentaje (mes)
- [x] 4.8 Crear endpoints API para datos de gráficas

### Subtareas activas Fase 4 (ejecución)
- [x] F4-A Actualizar `app/routes/admin.py` con ruta `estadisticas` y APIs JSON
- [x] F4-B Crear `app/templates/estadisticas.html`
- [x] F4-C Activar enlace “Estadísticas” en `app/templates/base_admin.html`
- [x] F4-D Agregar estilos en `app/static/admin.css`
- [x] F4-E Probar endpoints de estadísticas con `curl.exe`
- [ ] F4-F Verificar visualmente el módulo en navegador

## FASE 5: Facturación Electrónica DIAN
- [ ] 5.1 Investigar requisitos técnicos DIAN (factura electrónica Colombia)
- [ ] 5.2 Implementar generación de XML UBL 2.1
- [ ] 5.3 Implementar firma digital de facturas
- [ ] 5.4 Integrar envío a DIAN (SOAP/REST)
- [ ] 5.5 Crear template de factura PDF
- [ ] 5.6 Guardar historial de facturas electrónicas emitidas

### Subtareas activas Fase 5 (inicio)
- [ ] F5-A Revisar modelos actuales de facturación y campos faltantes para FE DIAN
- [ ] F5-B Definir estructura técnica UBL 2.1 y mapeo de datos del sistema
- [x] F5-C Diseñar modelo de historial de facturas electrónicas (tracking + estados)
- [x] F5-D Crear servicio base `einvoice_service` para generar XML inicial
- [x] F5-E Preparar configuración de entorno DIAN (sandbox/producción)
- [ ] F5-F Definir estrategia de firma digital e integración DIAN por etapas

## FASE 6: Testing y Verificación
- [ ] 6.1 Verificar cambio de estados en admin
- [ ] 6.2 Verificar visibilidad en catálogo público
- [ ] 6.3 Verificar menú hamburguesa responsive
- [ ] 6.4 Verificar cálculos de facturación
- [ ] 6.5 Verificar gráficas de estadísticas

## EJECUCIÓN ACTUAL (Fase 5)
- [x] 5X.1 Revisar `config.py` para variables DIAN
- [x] 5X.2 Agregar modelo `FacturaElectronica` en `app/models.py` (ya existía, validado sin duplicar)
- [x] 5X.3 Crear servicio `app/services/einvoice_service.py`
- [x] 5X.4 Crear migración Alembic para `factura_electronica` (omitido correctamente: ya existía en Fase 3)
- [x] 5X.5 Validar imports/arranque y actualizar checks F5-C/F5-D/F5-E

## EJECUCIÓN ACTUAL (Fase 5 - firma/envío incremental)
- [ ] 5Y.1 Extender `einvoice_service` con firma stub y sobre de envío DIAN
- [ ] 5Y.2 Crear `app/services/dian_client.py` desacoplado para sandbox
- [ ] 5Y.3 Agregar endpoint admin de prueba FE en `app/routes/admin.py`
- [ ] 5Y.4 Guardar trazabilidad FE en `FacturaElectronica` desde endpoint de prueba
- [ ] 5Y.5 Probar endpoint FE por curl (happy/error/edge) y actualizar checklist

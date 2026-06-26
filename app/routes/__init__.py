from .admin import admin_bp
from .auth import auth_bp
from .public import public_bp
from .publishing import publishing_bp


ENDPOINT_ALIASES = {
    "login": "auth.login",
    "logout": "auth.logout",
    "arriendo": "public.arriendo",
    "venta": "public.venta",
    "avaluo": "public.avaluo",
    "home": "public.home",
    "mostrar_inmuebles": "public.mostrar_inmuebles",
    "detalle_inmueble": "public.detalle_inmueble",
    "publicar": "publishing.publicar",
    "promocionar": "publishing.promocionar",
    "guardar_temp": "publishing.guardar_temp",
    "confirmar_envio": "publishing.confirmar_envio",
    "exportar_excel": "admin.exportar_excel",
    "detalle_arrendamiento": "admin.detalle_arrendamiento",
    "admin_preview_documento": "admin.admin_preview_documento",
    "admin_download_documento": "admin.admin_download_documento",
    "arrendar_inmueble": "admin.arrendar_inmueble",
    "cambiar_estado": "admin.cambiar_estado",
    "panel_admin": "admin.panel_admin",
    "admin_inmuebles": "admin.admin_inmuebles",
    "facturacion": "admin.facturacion",
    "detalle_facturacion": "admin.detalle_facturacion",
    "estadisticas": "admin.estadisticas",
    "api_estadisticas_estado_pagos": "admin.api_estadisticas_estado_pagos",
    "api_estadisticas_recaudado": "admin.api_estadisticas_recaudado",
    "api_estadisticas_dias_mora": "admin.api_estadisticas_dias_mora",
    "api_estadisticas_ingresos_gastos": "admin.api_estadisticas_ingresos_gastos",
    "api_estadisticas_gastos_porcentaje": "admin.api_estadisticas_gastos_porcentaje",
    "generar_fe_prueba": "admin.generar_fe_prueba",
    "activar_plan": "admin.activar_plan",
    "desactivar_plan": "admin.desactivar_plan",
    "nuevo_inmueble": "admin.nuevo_inmueble",
    "agregar_inmueble": "admin.agregar_inmueble",
    "eliminar_imagen": "admin.eliminar_imagen",
    "editar_inmueble": "admin.editar_inmueble",
    "reordenar_imagenes": "admin.reordenar_imagenes",
    "eliminar_inmueble": "admin.eliminar_inmueble",
}


def register_endpoint_aliases(app):
    rules_by_endpoint = {rule.endpoint: rule for rule in app.url_map.iter_rules()}

    for alias, actual_endpoint in ENDPOINT_ALIASES.items():
        if alias in app.view_functions:
            continue

        rule = rules_by_endpoint.get(actual_endpoint)
        if not rule:
            continue

        app.add_url_rule(
            rule.rule,
            endpoint=alias,
            view_func=app.view_functions[actual_endpoint],
            defaults=rule.defaults,
            methods=sorted(rule.methods - {"HEAD", "OPTIONS"}),
        )


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(publishing_bp)
    register_endpoint_aliases(app)

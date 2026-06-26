from __future__ import annotations

from datetime import datetime


class DianClient:
    """
    Cliente DIAN desacoplado (fase incremental).
    Esta implementación es un stub para sandbox/control interno.
    """

    def __init__(self, endpoint_url: str, environment: str = "sandbox"):
        self.endpoint_url = endpoint_url
        self.environment = (environment or "sandbox").strip().lower()

    def submit_invoice(self, envelope: dict) -> dict:
        """
        Simula envío a DIAN en entorno sandbox.
        Reemplazable por integración SOAP/REST real en fases posteriores.
        """
        invoice_number = envelope.get("invoice_number") if isinstance(envelope, dict) else None
        if not invoice_number:
            return {
                "ok": False,
                "status": "error",
                "message": "Envelope inválido: falta invoice_number",
                "track_id": None,
                "response_at": datetime.utcnow().isoformat() + "Z",
                "endpoint": self.endpoint_url,
                "environment": self.environment,
            }

        track_id = f"TRACK-{invoice_number}-{int(datetime.utcnow().timestamp())}"

        return {
            "ok": True,
            "status": "received",
            "message": "Factura recibida en sandbox (simulado)",
            "track_id": track_id,
            "response_at": datetime.utcnow().isoformat() + "Z",
            "endpoint": self.endpoint_url,
            "environment": self.environment,
        }

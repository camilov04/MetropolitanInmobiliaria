from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from xml.etree.ElementTree import Element, SubElement, tostring


def _money(value) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount}"


def validate_invoice_payload(payload: dict) -> tuple[bool, list[str]]:
    required = [
        "numero_factura",
        "fecha_emision",
        "cliente_nombre",
        "cliente_nit",
        "valor_total",
    ]
    errors = []
    for key in required:
        if not payload.get(key):
            errors.append(f"Falta campo requerido: {key}")

    if payload.get("valor_total") is not None:
        try:
            if Decimal(str(payload.get("valor_total"))) < 0:
                errors.append("valor_total no puede ser negativo")
        except Exception:
            errors.append("valor_total no es numérico válido")

    return (len(errors) == 0, errors)


def build_ubl_xml(payload: dict) -> str:
    """
    Genera XML base estilo UBL 2.1 (estructura inicial para sandbox).
    Nota: Esta versión es base técnica, no incluye firma digital ni CUFE final DIAN.
    """
    root = Element(
        "Invoice",
        attrib={
            "xmlns": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "xmlns:cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "xmlns:cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )

    SubElement(root, "cbc:UBLVersionID").text = "2.1"
    SubElement(root, "cbc:CustomizationID").text = "DIAN 2.1"
    SubElement(root, "cbc:ProfileExecutionID").text = str(payload.get("profile_execution_id", "2"))  # 2 sandbox
    SubElement(root, "cbc:ID").text = str(payload.get("numero_factura", ""))
    SubElement(root, "cbc:IssueDate").text = str(payload.get("fecha_emision", ""))
    SubElement(root, "cbc:IssueTime").text = str(payload.get("hora_emision", "00:00:00-05:00"))
    SubElement(root, "cbc:InvoiceTypeCode").text = str(payload.get("tipo_factura", "01"))
    SubElement(root, "cbc:DocumentCurrencyCode").text = str(payload.get("moneda", "COP"))

    accounting_customer_party = SubElement(root, "cac:AccountingCustomerParty")
    party = SubElement(accounting_customer_party, "cac:Party")
    party_tax_scheme = SubElement(party, "cac:PartyTaxScheme")
    SubElement(party_tax_scheme, "cbc:RegistrationName").text = str(payload.get("cliente_nombre", ""))
    company_id = SubElement(party_tax_scheme, "cbc:CompanyID")
    company_id.text = str(payload.get("cliente_nit", ""))
    company_id.set("schemeID", str(payload.get("cliente_tipo_doc", "31")))

    legal_monetary_total = SubElement(root, "cac:LegalMonetaryTotal")
    line_extension = SubElement(legal_monetary_total, "cbc:LineExtensionAmount")
    line_extension.text = _money(payload.get("valor_total", 0))
    line_extension.set("currencyID", str(payload.get("moneda", "COP")))

    payable_amount = SubElement(legal_monetary_total, "cbc:PayableAmount")
    payable_amount.text = _money(payload.get("valor_total", 0))
    payable_amount.set("currencyID", str(payload.get("moneda", "COP")))

    invoice_line = SubElement(root, "cac:InvoiceLine")
    SubElement(invoice_line, "cbc:ID").text = "1"
    SubElement(invoice_line, "cbc:InvoicedQuantity", attrib={"unitCode": "EA"}).text = "1"
    line_extension_amount = SubElement(invoice_line, "cbc:LineExtensionAmount")
    line_extension_amount.text = _money(payload.get("valor_total", 0))
    line_extension_amount.set("currencyID", str(payload.get("moneda", "COP")))

    item = SubElement(invoice_line, "cac:Item")
    SubElement(item, "cbc:Description").text = str(payload.get("descripcion_item", "Servicio de administración inmobiliaria"))

    price = SubElement(invoice_line, "cac:Price")
    price_amount = SubElement(price, "cbc:PriceAmount")
    price_amount.text = _money(payload.get("valor_total", 0))
    price_amount.set("currencyID", str(payload.get("moneda", "COP")))

    xml_bytes = tostring(root, encoding="utf-8", method="xml")
    return xml_bytes.decode("utf-8")


def build_sandbox_submission_payload(invoice_payload: dict, xml_content: str) -> dict:
    """
    Prepara payload base para integración sandbox DIAN.
    Stub técnico para etapas iniciales (sin transporte SOAP firmado).
    """
    return {
        "prepared_at": datetime.utcnow().isoformat() + "Z",
        "environment": "sandbox",
        "invoice_number": invoice_payload.get("numero_factura"),
        "customer_nit": invoice_payload.get("cliente_nit"),
        "xml": xml_content,
    }


def sign_invoice_xml(xml_content: str, software_pin: str = "") -> dict:
    """
    Firma stub (no criptográfica DIAN real).
    Retorna huella SHA-256 para trazabilidad técnica.
    """
    base = f"{xml_content}|{software_pin or ''}"
    digest = sha256(base.encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "signed_xml": xml_content,
        "signature_stub": digest,
    }


def build_dian_submission_envelope(invoice_payload: dict, signed_xml: str, signature_stub: str) -> dict:
    return {
        "prepared_at": datetime.utcnow().isoformat() + "Z",
        "environment": invoice_payload.get("dian_env", "sandbox"),
        "invoice_number": invoice_payload.get("numero_factura"),
        "customer_nit": invoice_payload.get("cliente_nit"),
        "signature_stub": signature_stub,
        "xml": signed_xml,
    }


def generate_invoice_xml(invoice_payload: dict) -> dict:
    """
    Flujo unificado:
    - valida payload
    - construye XML base UBL 2.1
    - prepara payload sandbox
    """
    is_valid, errors = validate_invoice_payload(invoice_payload)
    if not is_valid:
        return {
            "ok": False,
            "errors": errors,
            "xml": None,
            "sandbox_payload": None,
        }

    xml_content = build_ubl_xml(invoice_payload)
    sandbox_payload = build_sandbox_submission_payload(invoice_payload, xml_content)

    return {
        "ok": True,
        "errors": [],
        "xml": xml_content,
        "sandbox_payload": sandbox_payload,
    }


def generate_signed_invoice_envelope(invoice_payload: dict, software_pin: str = "") -> dict:
    """
    Flujo incremental:
    - genera XML base
    - aplica firma stub
    - construye sobre de envío DIAN
    """
    base = generate_invoice_xml(invoice_payload)
    if not base.get("ok"):
        return {
            "ok": False,
            "errors": base.get("errors", ["No se pudo generar XML"]),
            "xml": None,
            "signed_xml": None,
            "signature_stub": None,
            "dian_envelope": None,
        }

    sign_result = sign_invoice_xml(base["xml"], software_pin=software_pin)
    envelope = build_dian_submission_envelope(
        invoice_payload=invoice_payload,
        signed_xml=sign_result["signed_xml"],
        signature_stub=sign_result["signature_stub"],
    )

    return {
        "ok": True,
        "errors": [],
        "xml": base["xml"],
        "signed_xml": sign_result["signed_xml"],
        "signature_stub": sign_result["signature_stub"],
        "dian_envelope": envelope,
    }

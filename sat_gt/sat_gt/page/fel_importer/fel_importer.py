"""Backend methods for the FEL importer test page."""

from __future__ import annotations

import base64
from decimal import Decimal

import frappe

from sat_gt.fel.erpnext import factura_electronica_is_installed
from sat_gt.fel.matching import find_purchase_invoice_matches
from sat_gt.fel.parser import FELDocument, parse_fel_xml


@frappe.whitelist()
def parse_uploaded_xml(filename: str, content: str) -> dict:
	"""Parse one base64-encoded XML and return data for the test page."""
	try:
		raw_xml = base64.b64decode(content, validate=True)
		document = parse_fel_xml(raw_xml)
	except Exception as exc:
		return {"filename": filename, "ok": False, "error": str(exc)}

	result = {"filename": filename, "ok": True, "document": _serialize_document(document)}
	if factura_electronica_is_installed() and not document.is_credit_note:
		result["matches"] = _find_matches(document)
	else:
		result["matches"] = []
	return result


def _find_matches(document: FELDocument) -> list[dict]:
	"""Find candidates for display without modifying any ERPNext document."""
	invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"docstatus": ["!=", 2]},
		fields=["name", "supplier", "supplier_name", "facelec_nit_fproveedor", "grand_total", "currency"],
		limit_page_length=0,
	)
	matches = find_purchase_invoice_matches(document, invoices)
	return [
		{
			"name": candidate.document.name,
			"supplier": candidate.document.supplier,
			"supplier_name": candidate.document.supplier_name,
			"grand_total": str(candidate.document.grand_total),
			"currency": candidate.document.currency,
		}
		for candidate in matches
	]


def _serialize_document(document: FELDocument) -> dict:
	return {
		"uuid": document.uuid,
		"authorization_number": document.authorization_number,
		"authorization_series": document.authorization_series,
		"issuer_nit": document.issuer_nit,
		"issuer_name": document.issuer_name,
		"document_type": document.document_type,
		"emission_datetime": document.emission_datetime.isoformat(),
		"currency": document.currency,
		"grand_total": str(document.grand_total),
		"receiver_nit": document.receiver_nit,
		"receiver_name": document.receiver_name,
		"complements": list(document.complements),
		"taxes": [{"name": tax.name, "amount": str(tax.tax_amount)} for tax in document.taxes],
		"items": [
			{
				"line_number": item.line_number,
				"description": item.description,
				"quantity": str(item.quantity),
				"unit": item.unit,
				"unit_price": str(item.unit_price),
				"total": str(item.total),
			}
			for item in document.items
		],
	}

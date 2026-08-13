"""Backend methods for the FEL importer test page."""

from __future__ import annotations

import base64
from calendar import monthrange
from datetime import date
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
		result["supplier"] = _find_supplier(document)
		result["matches"] = _find_matches(document)
	else:
		result["matches"] = []
	return result


@frappe.whitelist()
def get_unmatched_purchase_invoices(month: str, total: str | None = None, currency: str | None = None) -> list[dict]:
	"""Return Purchase Invoices from a month without an assigned FEL UUID."""
	_require_fel_app()
	year, month_number = (int(value) for value in month.split("-"))
	start = date(year, month_number, 1)
	end = date(year, month_number, monthrange(year, month_number)[1])
	filters = {
		"posting_date": ["between", [start.isoformat(), end.isoformat()]],
		"numero_autorizacion_fel": ["in", ["", None]],
		"docstatus": ["!=", 2],
	}
	if currency:
		filters["currency"] = currency
	if total:
		filters["grand_total"] = ["between", [str(Decimal(total) - Decimal("0.01")), str(Decimal(total) + Decimal("0.01"))]]
	return frappe.get_all(
		"Purchase Invoice",
		filters=filters,
		fields=["name", "posting_date", "supplier", "supplier_name", "facelec_nit_fproveedor", "grand_total", "currency"],
		order_by="posting_date desc, name desc",
		limit_page_length=0,
	)


@frappe.whitelist()
def associate_uuid_manually(purchase_invoice: str, content: str, tolerance: str = "0.01") -> dict:
	"""Associate a selected existing invoice with the UUID from an XML."""
	_require_fel_app()
	document = parse_fel_xml(_decode_xml(content))
	invoice = frappe.get_doc("Purchase Invoice", purchase_invoice)
	if invoice.numero_autorizacion_fel:
		frappe.throw("La Purchase Invoice ya tiene un UUID asociado")
	if frappe.db.exists("Purchase Invoice", {"numero_autorizacion_fel": document.uuid}):
		frappe.throw("El UUID ya está asociado a otra Purchase Invoice")
	if invoice.currency != document.currency:
		frappe.throw("La moneda de la factura no coincide con la del XML")
	if abs(Decimal(str(invoice.grand_total)) - document.grand_total) > Decimal(tolerance):
		frappe.throw("El total de la factura no coincide con el XML")

	invoice.numero_autorizacion_fel = document.uuid
	invoice.serie_original_del_documento = document.authorization_series or ""
	invoice.save()
	return {"name": invoice.name, "uuid": document.uuid}


@frappe.whitelist()
def create_imported_suppliers(documents: str) -> dict:
	"""Create missing suppliers in the dedicated imported supplier group."""
	_require_fel_app()
	rows = frappe.parse_json(documents) if isinstance(documents, str) else documents
	group_name = "Proveedores Importados"
	if not frappe.db.exists("Supplier Group", group_name):
		frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": group_name}).insert()

	created = []
	existing = []
	errors = []
	for row in rows:
		try:
			document = parse_fel_xml(_decode_xml(row["content"]))
			supplier = frappe.db.get_value("Supplier", {"facelec_nit_proveedor": document.issuer_nit}, "name")
			if supplier:
				existing.append({"nit": document.issuer_nit, "name": supplier})
				continue
			supplier_doc = frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": document.issuer_name or document.issuer_nit,
					"supplier_group": group_name,
					"supplier_type": "Company",
					"tax_id": document.issuer_nit,
					"facelec_nit_proveedor": document.issuer_nit,
				}
			).insert()
			created.append({"nit": document.issuer_nit, "name": supplier_doc.name})
		except Exception as exc:
			errors.append({"filename": row.get("filename", ""), "error": str(exc)})
	return {"group": group_name, "created": created, "existing": existing, "errors": errors}


@frappe.whitelist()
def create_purchase_invoice_draft(
	content: str,
	company: str,
	supplier: str | None = None,
	default_item: str | None = None,
	expense_account: str | None = None,
) -> dict:
	"""Create an unsubmitted Purchase Invoice draft from a FEL XML.

	The initial draft uses the XML line total as the gross rate. Tax account
	mapping remains explicit in the next accounting configuration step.
	"""
	_require_fel_app()
	document = parse_fel_xml(_decode_xml(content))
	if document.is_credit_note:
		frappe.throw("Las notas de crédito se implementarán como un flujo separado")
	if frappe.db.exists("Purchase Invoice", {"numero_autorizacion_fel": document.uuid}):
		frappe.throw("El UUID ya está asociado a una Purchase Invoice")

	matched_supplier = _find_supplier(document)
	if not matched_supplier:
		frappe.throw(
			f"No existe un proveedor con el NIT {document.issuer_nit}. "
			"Créalo primero usando Crear proveedores importados."
		)
	if supplier and supplier != matched_supplier["name"]:
		frappe.throw("El proveedor no coincide con el NIT del XML")
	supplier = matched_supplier["name"]
	if not default_item and not expense_account:
		frappe.throw("Selecciona un Item por defecto o una cuenta de gasto")

	invoice = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": supplier,
			"posting_date": document.emission_datetime.date().isoformat(),
			"bill_no": document.uuid,
			"bill_date": document.emission_datetime.date().isoformat(),
			"currency": document.currency,
			"facelec_nit_fproveedor": document.issuer_nit,
			"numero_autorizacion_fel": document.uuid,
			"serie_original_del_documento": document.authorization_series or "",
		}
	)
	for item in document.items:
		row = {
			"description": item.description,
			"qty": item.quantity,
			"rate": item.total / item.quantity,
		}
		if default_item:
			row["item_code"] = default_item
		if expense_account:
			row["expense_account"] = expense_account
		invoice.append("items", row)
	invoice.insert()
	return {"name": invoice.name, "uuid": document.uuid, "warning": "Borrador creado con importes brutos; revisar impuestos antes de contabilizar."}


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


def _decode_xml(content: str) -> bytes:
	try:
		return base64.b64decode(content, validate=True)
	except Exception as exc:
		raise ValueError("Contenido XML inválido") from exc


def _find_supplier(document: FELDocument) -> dict | None:
	"""Find a supplier by FEL NIT, accepting common hyphen formatting."""
	variants = {document.issuer_nit, document.issuer_nit.replace("-", "")}
	for nit in variants:
		for field in ("facelec_nit_proveedor", "tax_id"):
			name = frappe.db.get_value("Supplier", {field: nit}, "name")
			if name:
				return frappe.db.get_value(
					"Supplier",
					name,
					["name", "supplier_name", "facelec_nit_proveedor"],
					as_dict=True,
				)
	return None


def _require_fel_app() -> None:
	if not factura_electronica_is_installed():
		frappe.throw("La app factura_electronica es requerida para esta operación")


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

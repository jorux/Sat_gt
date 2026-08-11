"""ERPNext integration for FEL purchase invoice matching.

This module imports Frappe only when called, so the parser and matcher remain
usable in unit tests without a running Bench site.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sat_gt.fel.matching import MatchCandidate, find_purchase_invoice_matches, link_purchase_invoice
from sat_gt.fel.parser import FELDocument


FACTURA_ELECTRONICA_APP = "factura_electronica"
PURCHASE_INVOICE_FIELDS = (
	"name",
	"facelec_nit_fproveedor",
	"grand_total",
	"currency",
	"numero_autorizacion_fel",
)


def factura_electronica_is_installed() -> bool:
	"""Return whether the Guatemala electronic invoicing app is installed."""
	import frappe

	return FACTURA_ELECTRONICA_APP in frappe.get_installed_apps()


def find_erpnext_purchase_invoice_matches(
	fel_document: FELDocument,
	*,
	company: str | None = None,
	tolerance: Decimal = Decimal("0.01"),
) -> list[MatchCandidate]:
	"""Find existing ERPNext purchase invoices matching a FEL document."""
	_require_factura_electronica()
	import frappe

	filters: dict[str, Any] = {"docstatus": ["!=", 2]}
	if company:
		filters["company"] = company
	invoices = frappe.get_all("Purchase Invoice", filters=filters, fields=list(PURCHASE_INVOICE_FIELDS))
	return find_purchase_invoice_matches(fel_document, invoices, tolerance=tolerance)


def link_erpnext_purchase_invoice(
	purchase_invoice_name: str,
	fel_document: FELDocument,
	*,
	tolerance: Decimal = Decimal("0.01"),
	ignore_permissions: bool = False,
) -> Any:
	"""Assign FEL UUID and series to an ERPNext Purchase Invoice.

	The document is validated against the same NIT, total and currency rules
	used by the search. The caller can commit the save as part of its workflow.
	"""
	_require_factura_electronica()
	import frappe

	invoices = find_erpnext_purchase_invoice_matches(fel_document, tolerance=tolerance)
	if not any(candidate.document.name == purchase_invoice_name for candidate in invoices):
		frappe.throw("La Purchase Invoice no coincide con el XML por NIT, total y moneda")
	invoice = frappe.get_doc("Purchase Invoice", purchase_invoice_name)

	all_invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"numero_autorizacion_fel": fel_document.uuid},
		fields=["name", "numero_autorizacion_fel"],
	)
	link_purchase_invoice(
		invoice,
		fel_document,
		all_purchase_invoices=all_invoices,
		tolerance=tolerance,
	)
	invoice.save(ignore_permissions=ignore_permissions)
	return invoice


def _require_factura_electronica() -> None:
	if not factura_electronica_is_installed():
		raise RuntimeError(
			"La app factura_electronica es requerida para validar Purchase Invoice FEL"
		)

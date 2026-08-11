"""Matching FEL documents with existing ERPNext purchase invoices."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from sat_gt.fel.parser import FELDocument


class MatchError(ValueError):
	"""Raised when a purchase invoice cannot safely be linked."""


class DuplicateUUIDError(MatchError):
	"""Raised when a UUID is already linked to another invoice."""


@dataclass(frozen=True)
class MatchCandidate:
	document: Any
	matched_fields: tuple[str, ...]


def find_purchase_invoice_matches(
	fel_document: FELDocument,
	purchase_invoices: Iterable[Any],
	*,
	tolerance: Decimal = Decimal("0.01"),
	nit_fields: tuple[str, ...] = ("facelec_nit_fproveedor", "supplier_tax_id", "nit", "tax_id"),
	total_fields: tuple[str, ...] = ("grand_total", "total"),
	currency_fields: tuple[str, ...] = ("currency", "transaction_currency"),
	) -> list[MatchCandidate]:
	"""Return invoices matching issuer NIT, total and currency.

	FACT and FCAM intentionally share this matching path. Date is not a
	required key because invoice entry dates commonly differ from emission
	dates; it can be used as a UI tie-breaker later.
	"""
	if fel_document.is_credit_note:
		return []

	results = []
	for invoice in purchase_invoices:
		nit = _first_value(invoice, nit_fields)
		total = _first_value(invoice, total_fields)
		currency = _first_value(invoice, currency_fields)
		if _normalize_nit(nit) != _normalize_nit(fel_document.issuer_nit):
			continue
		if total is None or abs(_decimal(total) - fel_document.grand_total) > tolerance:
			continue
		if currency and currency.upper() != fel_document.currency.upper():
			continue
		results.append(MatchCandidate(invoice, ("issuer_nit", "grand_total", "currency")))
	return results


def link_purchase_invoice(
	invoice: Any,
	fel_document: FELDocument,
	*,
	all_purchase_invoices: Iterable[Any] | None = None,
	tolerance: Decimal = Decimal("0.01"),
	uuid_field: str = "numero_autorizacion_fel",
	series_field: str = "serie_original_del_documento",
) -> Any:
	"""Validate and assign a FEL UUID to an ERPNext-like document.

	The function supports Frappe documents and plain objects/dictionaries,
	which keeps the matching logic testable outside a Bench site. The caller
	should invoke ``save`` after this function returns.
	"""
	candidates = find_purchase_invoice_matches(
		fel_document,
		[invoice],
		tolerance=tolerance,
	)
	if not candidates:
		raise MatchError("La Purchase Invoice no coincide por NIT, total y moneda")

	current_uuid = _get_value(invoice, uuid_field)
	if current_uuid and current_uuid != fel_document.uuid:
		raise DuplicateUUIDError(f"La factura ya tiene UUID asignado: {current_uuid}")

	if all_purchase_invoices is not None:
		for other in all_purchase_invoices:
			if other is invoice:
				continue
			if _get_value(other, uuid_field) == fel_document.uuid:
				raise DuplicateUUIDError(f"El UUID ya está asignado a otra factura: {fel_document.uuid}")

	_set_value(invoice, uuid_field, fel_document.uuid)
	_set_value(invoice, series_field, fel_document.authorization_series or "")
	return invoice


def _first_value(document: Any, fields: tuple[str, ...]) -> Any:
	for field in fields:
		value = _get_value(document, field)
		if value not in (None, ""):
			return value
	return None


def _get_value(document: Any, field: str) -> Any:
	if isinstance(document, dict):
		return document.get(field)
	return getattr(document, field, None)


def _set_value(document: Any, field: str, value: Any) -> None:
	if isinstance(document, dict):
		document[field] = value
	else:
		setattr(document, field, value)


def _normalize_nit(value: Any) -> str:
	return "".join(str(value or "").upper().split()).replace("-", "")


def _decimal(value: Any) -> Decimal:
	return value if isinstance(value, Decimal) else Decimal(str(value))

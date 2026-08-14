"""Build Purchase Invoice tax rows directly from FEL XML values."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sat_gt.fel.parser import FELDocument, FELItem


class FELTaxMappingError(ValueError):
	"""Raised when an XML tax has no configured ERPNext account."""


def tax_amounts_by_name(document: FELDocument) -> dict[str, Decimal]:
	"""Return the tax totals reported by FEL, preserving XML tax names."""
	if document.taxes:
		return {tax.name: tax.tax_amount for tax in document.taxes if tax.name}

	amounts: defaultdict[str, Decimal] = defaultdict(Decimal)
	for item in document.items:
		for tax in item.taxes:
			amounts[tax.name] += tax.tax_amount
	return dict(amounts)


def net_line_total(item: FELItem) -> Decimal:
	"""Return a line amount excluding the taxes embedded in the XML total."""
	return item.total - sum((tax.tax_amount for tax in item.taxes), Decimal("0"))


def build_purchase_invoice_tax_rows(
	document: FELDocument,
	account_by_tax: dict[str, str],
) -> list[dict]:
	"""Build ERPNext ``Purchase Taxes and Charges`` rows using actual amounts.

	No tax template is consulted. Each XML tax must be mapped to an account by
	the user before a draft can be created.
	"""
	amounts = tax_amounts_by_name(document)
	missing = sorted(name for name in amounts if not account_by_tax.get(name))
	if missing:
		raise FELTaxMappingError("Faltan cuentas para impuestos: " + ", ".join(missing))

	return [
		{
			"charge_type": "Actual",
			"account_head": account_by_tax[name],
			"description": name,
			"tax_amount": amount,
			"rate": 0,
		}
		for name, amount in amounts.items()
	]

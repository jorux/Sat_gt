"""Backend for the FEL tax account assignment page."""

from __future__ import annotations

import frappe


@frappe.whitelist()
def list_mappings(company: str | None = None) -> list[dict]:
	filters = {"company": company} if company else {}
	return frappe.get_all(
		"FEL Tax Account Mapping",
		filters=filters,
		fields=["name", "company", "tax_name", "account_head", "enabled"],
		order_by="company, tax_name",
		limit_page_length=0,
	)


@frappe.whitelist()
def save_mapping(company: str, tax_name: str, account_head: str, enabled: int = 1) -> dict:
	if not frappe.db.exists("Company", company):
		frappe.throw("La compañía no existe")
	if frappe.db.get_value("Account", account_head, "company") != company:
		frappe.throw("La cuenta contable no pertenece a la compañía seleccionada")

	tax_name = tax_name.strip().upper()
	existing = frappe.db.get_value(
		"FEL Tax Account Mapping",
		{"company": company, "tax_name": tax_name},
		"name",
	)
	if existing:
		doc = frappe.get_doc("FEL Tax Account Mapping", existing)
	else:
		doc = frappe.get_doc({"doctype": "FEL Tax Account Mapping", "company": company, "tax_name": tax_name})
	doc.account_head = account_head
	doc.enabled = int(enabled)
	doc.save() if doc.name and not doc.is_new() else doc.insert()
	return {"name": doc.name, "company": company, "tax_name": tax_name, "account_head": account_head, "enabled": doc.enabled}

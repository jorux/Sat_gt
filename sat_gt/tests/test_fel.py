from decimal import Decimal
from pathlib import Path

import pytest

from sat_gt.fel.matching import DuplicateUUIDError, find_purchase_invoice_matches, link_purchase_invoice
from sat_gt.fel.parser import FELDocument, FELParseError, parse_fel_xml


ROOT = Path(__file__).parents[1]
SAMPLES = ROOT / "sat_gt" / "Samples"


def test_parse_fact_sample():
	document = parse_fel_xml(SAMPLES / "015AF78D-35F6-4BA0-82A5-9BE6EE1B04F3.xml")

	assert document.document_type == "FCAM"
	assert document.uuid == "015AF78D-35F6-4BA0-82A5-9BE6EE1B04F3"
	assert document.issuer_nit == "67351557"
	assert document.currency == "GTQ"
	assert document.grand_total == Decimal("13535.1250")
	assert document.items[0].taxes[0].name == "IVA"
	assert "AbonosFacturaCambiaria" in document.complements


def test_parse_all_july_samples():
	samples = list(SAMPLES.glob("*.xml"))
	assert samples

	for sample in samples:
		document = parse_fel_xml(sample)
		assert document.uuid == sample.stem
		assert document.issuer_nit
		assert document.grand_total >= 0


def test_matching_uses_factura_electronica_fields():
	document = parse_fel_xml(SAMPLES / "015AF78D-35F6-4BA0-82A5-9BE6EE1B04F3.xml")
	invoices = [
		{
			"name": "PINV-0001",
			"facelec_nit_fproveedor": "67351557",
			"grand_total": Decimal("13535.13"),
			"currency": "GTQ",
		},
		{
			"name": "PINV-0002",
			"facelec_nit_fproveedor": "99999999",
			"grand_total": Decimal("13535.13"),
			"currency": "GTQ",
		},
	]

	matches = find_purchase_invoice_matches(document, invoices)

	assert [candidate.document["name"] for candidate in matches] == ["PINV-0001"]


def test_link_assigns_uuid_and_series():
	document = parse_fel_xml(SAMPLES / "015AF78D-35F6-4BA0-82A5-9BE6EE1B04F3.xml")
	invoice = {
		"facelec_nit_fproveedor": "67351557",
		"grand_total": Decimal("13535.13"),
		"currency": "GTQ",
	}

	link_purchase_invoice(invoice, document)

	assert invoice["numero_autorizacion_fel"] == document.uuid
	assert invoice["serie_original_del_documento"] == "015AF78D"


def test_link_rejects_duplicate_uuid():
	document = parse_fel_xml(SAMPLES / "015AF78D-35F6-4BA0-82A5-9BE6EE1B04F3.xml")
	invoice = {
		"facelec_nit_fproveedor": "67351557",
		"grand_total": Decimal("13535.13"),
		"currency": "GTQ",
	}
	other_invoice = {"numero_autorizacion_fel": document.uuid}

	with pytest.raises(DuplicateUUIDError):
		link_purchase_invoice(invoice, document, all_purchase_invoices=[invoice, other_invoice])


def test_invalid_document_is_rejected():
	with pytest.raises(FELParseError):
		parse_fel_xml(b"<not-fel />")

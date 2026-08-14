"""Parse Guatemala SAT FEL XML documents.

The parser deliberately uses local XML names instead of hard-coding namespace
prefixes. Certifiers produce the same FEL schema with different prefixes,
namespace declarations, whitespace and XML encodings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO
from xml.etree import ElementTree as ET


class FELParseError(ValueError):
	"""Raised when an XML file is not a readable FEL document."""


@dataclass(frozen=True)
class FELTax:
	name: str
	taxable_amount: Decimal | None
	tax_amount: Decimal


@dataclass(frozen=True)
class FELItem:
	line_number: int
	item_type: str | None
	description: str
	quantity: Decimal
	unit: str | None
	unit_price: Decimal
	price: Decimal
	discount: Decimal
	total: Decimal
	taxes: tuple[FELTax, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FELDocument:
	uuid: str
	authorization_number: str | None
	authorization_series: str | None
	issuer_nit: str
	issuer_name: str
	receiver_nit: str | None
	receiver_name: str | None
	document_type: str
	emission_datetime: datetime
	currency: str
	grand_total: Decimal
	items: tuple[FELItem, ...] = field(default_factory=tuple)
	taxes: tuple[FELTax, ...] = field(default_factory=tuple)
	complements: tuple[str, ...] = field(default_factory=tuple)
	raw_xml: bytes = b""

	@property
	def is_credit_note(self) -> bool:
		return self.document_type == "NCRE"


def parse_fel_xml(source: str | bytes | bytearray | Path | BinaryIO) -> FELDocument:
	"""Parse a FEL XML string, bytes, path or binary stream."""
	try:
		raw_xml = _read_source(source)
		root = ET.fromstring(raw_xml)
	except (OSError, ET.ParseError, TypeError, ValueError) as exc:
		raise FELParseError(f"No se pudo leer el XML FEL: {exc}") from exc

	if _local_name(root.tag) != "GTDocumento":
		raise FELParseError("El documento no es un GTDocumento FEL")

	data = _first(root, "DatosEmision")
	certification = _first(root, "Certificacion")
	general = _first(data, "DatosGenerales")
	issuer = _first(data, "Emisor")
	receiver = _first(data, "Receptor")
	authorization = _first(certification, "NumeroAutorizacion")

	if data is None or general is None or issuer is None or certification is None:
		raise FELParseError("El XML FEL no contiene la estructura fiscal requerida")

	uuid = _text(authorization)
	issuer_nit = _attribute(issuer, "NITEmisor")
	grand_total = _decimal(_text(_first(data, "GranTotal")), "GranTotal")
	if not uuid or not issuer_nit:
		raise FELParseError("El XML FEL no contiene UUID o NITEmisor")

	items = tuple(_parse_item(item) for item in _children(_first(data, "Items"), "Item"))
	taxes = tuple(_parse_total_tax(tax) for tax in _children(_first(data, "TotalImpuestos"), "TotalImpuesto"))
	complements = tuple(
		name
		for complement in _children(_first(data, "Complementos"), "Complemento")
		if (name := (_attribute(complement, "NombreComplemento") or _local_name(complement.tag)))
	)

	return FELDocument(
		uuid=uuid,
		authorization_number=_attribute(authorization, "Numero"),
		authorization_series=_attribute(authorization, "Serie"),
		issuer_nit=issuer_nit,
		issuer_name=_attribute(issuer, "NombreEmisor") or "",
		receiver_nit=_attribute(receiver, "IDReceptor"),
		receiver_name=_attribute(receiver, "NombreReceptor"),
		document_type=_attribute(general, "Tipo") or "",
		emission_datetime=_datetime(_attribute(general, "FechaHoraEmision")),
		currency=_attribute(general, "CodigoMoneda") or "GTQ",
		grand_total=grand_total,
		items=items,
		taxes=taxes,
		complements=complements,
		raw_xml=raw_xml,
	)


def _parse_item(item: ET.Element) -> FELItem:
	return FELItem(
		line_number=int(_attribute(item, "NumeroLinea") or "0"),
		item_type=_attribute(item, "BienOServicio"),
		description=_text(_first(item, "Descripcion")) or "",
		quantity=_decimal(_text(_first(item, "Cantidad")), "Cantidad"),
		unit=_text(_first(item, "UnidadMedida")),
		unit_price=_decimal(_text(_first(item, "PrecioUnitario")), "PrecioUnitario"),
		price=_decimal(_text(_first(item, "Precio")), "Precio"),
		discount=_decimal(_text(_first(item, "Descuento")) or "0", "Descuento"),
		total=_decimal(_text(_first(item, "Total")), "Total"),
		taxes=tuple(_parse_item_tax(tax) for tax in _children(_first(item, "Impuestos"), "Impuesto")),
	)


def _parse_item_tax(tax: ET.Element) -> FELTax:
	return FELTax(
		name=_text(_first(tax, "NombreCorto")) or "",
		taxable_amount=_optional_decimal(_text(_first(tax, "MontoGravable"))),
		tax_amount=_decimal(_text(_first(tax, "MontoImpuesto")), "MontoImpuesto"),
	)


def _parse_total_tax(tax: ET.Element) -> FELTax:
	return FELTax(
		name=_attribute(tax, "NombreCorto") or "",
		taxable_amount=None,
		tax_amount=_decimal(_attribute(tax, "TotalMontoImpuesto"), "TotalMontoImpuesto"),
	)


def _read_source(source: str | bytes | bytearray | Path | BinaryIO) -> bytes:
	if isinstance(source, Path):
		return source.read_bytes()
	if isinstance(source, (bytes, bytearray)):
		return bytes(source)
	if hasattr(source, "read"):
		return source.read()
	if isinstance(source, str):
		return source.encode("utf-8")
	raise TypeError("source debe ser XML, bytes, Path o un archivo binario")


def _local_name(tag: str) -> str:
	return tag.rsplit("}", 1)[-1]


def _first(element: ET.Element | None, name: str) -> ET.Element | None:
	if element is None:
		return None
	return next((child for child in element.iter() if _local_name(child.tag) == name), None)


def _children(element: ET.Element | None, name: str) -> list[ET.Element]:
	if element is None:
		return []
	return [child for child in list(element) if _local_name(child.tag) == name]


def _text(element: ET.Element | None) -> str | None:
	return element.text.strip() if element is not None and element.text else None


def _attribute(element: ET.Element | None, name: str) -> str | None:
	value = element.attrib.get(name) if element is not None else None
	return value.strip() if value else None


def _decimal(value: str | None, field_name: str) -> Decimal:
	if not value:
		raise FELParseError(f"Falta el campo numérico FEL {field_name}")
	try:
		return Decimal(value)
	except InvalidOperation as exc:
		raise FELParseError(f"El campo FEL {field_name} no es numérico: {value}") from exc


def _optional_decimal(value: str | None) -> Decimal | None:
	return _decimal(value, "valor") if value else None


def _datetime(value: str | None) -> datetime:
	if not value:
		raise FELParseError("Falta FechaHoraEmision")
	try:
		return datetime.fromisoformat(value)
	except ValueError as exc:
		raise FELParseError(f"FechaHoraEmision inválida: {value}") from exc

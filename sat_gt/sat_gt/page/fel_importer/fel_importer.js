frappe.pages["fel-importer"].on_page_load = function (wrapper) {
	new SatGtFelImporter(wrapper);
};

class SatGtFelImporter {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Importador FEL"),
			single_column: true,
		});
		this.render();
	}

	render() {
		this.page.main.html(`
			<div class="fel-importer">
				<div class="fel-importer-intro">
					<h3>${__("Probar XML FEL")}</h3>
					<p class="text-muted">${__("Selecciona uno o varios XML. Se parsearán y se buscarán coincidencias contra Purchase Invoice sin modificar documentos.")}</p>
				</div>
				<div class="form-group">
					<label>${__("Archivos XML")}</label>
					<input class="form-control fel-files" type="file" accept=".xml,text/xml" multiple>
				</div>
				<div class="form-row align-items-end mb-3">
					<div class="form-group col-sm-4 mb-0">
						<label>${__("Mes para asociación manual")}</label>
						<input class="form-control fel-month" type="month">
					</div>
					<div class="col-sm-8 text-muted small pb-2">${__("Busca Purchase Invoice sin UUID y permite asociarla por total.")}</div>
				</div>
				<div class="fel-actions"></div>
				<div class="fel-results"></div>
			</div>
		`);
		this.$files = this.page.main.find(".fel-files");
		this.$actions = this.page.main.find(".fel-actions");
		this.$results = this.page.main.find(".fel-results");
		this.$month = this.page.main.find(".fel-month");
		this.$files.on("change", () => this.showSelectedFiles());
	}

	showSelectedFiles() {
		const files = Array.from(this.$files[0].files || []);
		this.$actions.empty();
		this.$results.empty();
		if (!files.length) return;

		const button = $(`<button class="btn btn-primary">${__("Parsear archivos")}</button>`);
		button.on("click", () => this.parseFiles(files, button));
		this.$actions.append(button);
		this.$actions.append(`<span class="text-muted ml-3">${files.length} ${__("archivo(s) seleccionado(s)")}</span>`);
	}

	async parseFiles(files, button) {
		button.prop("disabled", true).text(__("Procesando..."));
		this.$results.html(`<div class="text-muted">${__("Analizando XML...")}</div>`);
		const results = [];
		for (const file of files) {
			try {
				const content = await this.readAsBase64(file);
				const response = await frappe.call({
					method: "sat_gt.sat_gt.page.fel_importer.fel_importer.parse_uploaded_xml",
					args: { filename: file.name, content },
				});
				const result = response.message;
				result.content = content;
				results.push(result);
			} catch (error) {
				results.push({ filename: file.name, ok: false, error: error.message || String(error) });
			}
		}
		this.results = results;
		this.renderResults(results);
		this.renderSupplierAction(results);
		button.prop("disabled", false).text(__("Parsear archivos"));
	}

	readAsBase64(file) {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(reader.result.split(",")[1]);
			reader.onerror = () => reject(reader.error || new Error(__("No se pudo leer el archivo")));
			reader.readAsDataURL(file);
		});
	}

	renderResults(results) {
		this.$results.empty();
		results.forEach((result) => {
			this.$results.append(result.ok ? this.documentCard(result) : this.errorCard(result));
		});
		this.$results.find(".fel-find-month").on("click", (event) => {
			const result = results[Number($(event.currentTarget).data("result-index"))];
			this.findMonthlyInvoice(result);
		});
		this.$results.find(".fel-create-draft").on("click", (event) => {
			const result = results[Number($(event.currentTarget).data("result-index"))];
			this.createDraft(result);
		});
	}

	renderSupplierAction(results) {
		this.$actions.find(".fel-suppliers").remove();
		const documents = results.filter((result) => result.ok);
		if (!documents.length) return;
		const button = $(`<button class="btn btn-secondary ml-2 fel-suppliers">${__("Crear proveedores importados")}</button>`);
		button.on("click", () => this.createSuppliers(documents, button));
		this.$actions.append(button);
	}

	createSuppliers(results, button) {
		frappe.confirm(
			__("Se crearán proveedores faltantes en el grupo Proveedores Importados. ¿Continuar?"),
			() => {
				button.prop("disabled", true);
				frappe.call({
					method: "sat_gt.sat_gt.page.fel_importer.fel_importer.create_imported_suppliers",
					args: { documents: JSON.stringify(results.map((result) => ({ filename: result.filename, content: result.content }))) },
				}).then((response) => {
					const data = response.message;
					frappe.msgprint(__("Creados: {0}. Existentes: {1}. Errores: {2}.", [data.created.length, data.existing.length, data.errors.length]));
					button.prop("disabled", false);
				});
			},
		);
	}

	findMonthlyInvoice(result) {
		if (!this.$month.val()) {
			frappe.msgprint(__("Selecciona un mes para buscar la factura."));
			return;
		}
		frappe.call({
			method: "sat_gt.sat_gt.page.fel_importer.fel_importer.get_unmatched_purchase_invoices",
			args: { month: this.$month.val(), total: result.document.grand_total, currency: result.document.currency },
		}).then((response) => {
			const candidates = response.message || [];
			if (!candidates.length) {
				frappe.msgprint(__("No hay facturas sin UUID con ese total en el mes seleccionado."));
				return;
			}
			const options = candidates.map((candidate) => candidate.name).join("\n");
			frappe.prompt(
				[{ fieldname: "invoice", fieldtype: "Select", label: __("Purchase Invoice"), options }],
				(values) => this.associateInvoice(values.invoice, result),
				__("Asociar UUID"),
				__("Asociar"),
			);
		});
	}

	associateInvoice(invoice, result) {
		frappe.call({
			method: "sat_gt.sat_gt.page.fel_importer.fel_importer.associate_uuid_manually",
			args: { purchase_invoice: invoice, content: result.content },
		}).then(() => {
			frappe.msgprint(__("UUID asociado correctamente."));
		});
	}

	createDraft(result) {
		const taxFields = (result.document.taxes || []).map((tax) => ({
			fieldname: this.taxFieldName(tax.name),
			fieldtype: "Link",
			options: "Account",
			label: `${__("Cuenta")} ${tax.name} (${tax.amount})`,
			reqd: 1,
		}));
		frappe.prompt(
			[
				{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Compañía"), reqd: 1 },
				{ fieldname: "default_item", fieldtype: "Link", options: "Item", label: __("Item por defecto") },
				{ fieldname: "expense_account", fieldtype: "Data", label: __("Cuenta de gasto (si no usa Item)") },
				...taxFields,
			],
			(values) => {
				const taxAccounts = {};
				(result.document.taxes || []).forEach((tax) => {
					taxAccounts[tax.name] = values[this.taxFieldName(tax.name)];
				});
				frappe.call({
					method: "sat_gt.sat_gt.page.fel_importer.fel_importer.create_purchase_invoice_draft",
					args: { ...values, tax_accounts: JSON.stringify(taxAccounts), content: result.content },
				}).then((response) => {
					frappe.msgprint(`${__("Borrador creado")}: ${response.message.name}<br>${response.message.warning}`);
				});
			},
			__("Crear borrador"),
			__("Crear"),
		);
	}

	taxFieldName(name) {
		return `tax_account_${name.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
	}

		documentCard(result) {
		const doc = result.document;
		const matches = result.matches || [];
		const matchHtml = matches.length
			? matches.map((match) => `<li><a href="/app/purchase-invoice/${encodeURIComponent(match.name)}">${frappe.utils.escape_html(match.name)}</a> · ${frappe.utils.escape_html(match.supplier_name || match.supplier || "")} · ${match.currency} ${match.grand_total}</li>`).join("")
			: `<li class="text-muted">${__("Factura no ingresada")}</li>`;
		const items = (doc.items || []).map((item) => `<tr><td>${item.line_number}</td><td>${frappe.utils.escape_html(item.description)}</td><td>${item.quantity} ${item.unit || ""}</td><td class="text-right">${item.total}</td></tr>`).join("");
		const taxes = (doc.taxes || []).map((tax) => `${frappe.utils.escape_html(tax.name)}: ${tax.amount}`).join(" · ") || __("Sin impuestos");

		return $(
			`<div class="card mb-3">
				<div class="card-header"><strong>${frappe.utils.escape_html(result.filename)}</strong><span class="indicator-pill green ml-2">${doc.document_type}</span>${result.already_imported ? `<span class="indicator-pill orange ml-2">${__("Ya importado")}</span>` : ""}</div>
				<div class="card-body">
					<div class="row">
						${this.field(__("UUID"), doc.uuid, "col-sm-6")}
						${this.field(__("Proveedor"), `${doc.issuer_name} (${doc.issuer_nit})`, "col-sm-6")}
						${this.field(__("Proveedor ERPNext"), result.supplier ? `${result.supplier.supplier_name} (${result.supplier.name})` : __("No existe proveedor con este NIT"), "col-sm-6")}
						${this.field(__("Total"), `${doc.currency} ${doc.grand_total}`, "col-sm-3")}
						${this.field(__("Impuestos XML"), taxes, "col-sm-5")}
						${this.field(__("Emisión"), doc.emission_datetime, "col-sm-5")}
						${this.field(__("Complementos"), (doc.complements || []).join(", ") || "-", "col-sm-4")}
					</div>
					<div class="fel-card-actions mb-3"><button class="btn btn-xs btn-secondary fel-find-month" data-result-index="${this.results ? this.results.indexOf(result) : 0}">${__("Buscar por mes y total")}</button><button class="btn btn-xs btn-primary ml-2 fel-create-draft" data-result-index="${this.results ? this.results.indexOf(result) : 0}">${__("Crear borrador")}</button></div>
					<h5>${__("Coincidencias")}</h5><ul>${matchHtml}</ul>
					<h5>${__("Líneas")}</h5>
					<table class="table table-bordered table-sm"><thead><tr><th>#</th><th>${__("Descripción")}</th><th>${__("Cantidad")}</th><th class="text-right">${__("Total")}</th></tr></thead><tbody>${items}</tbody></table>
				</div>
			</div>`
		);
	}

	field(label, value, className) {
		return `<div class="${className} mb-3"><div class="text-muted small">${label}</div><div>${frappe.utils.escape_html(String(value || "-"))}</div></div>`;
	}

	errorCard(result) {
		return $(`<div class="alert alert-danger"><strong>${frappe.utils.escape_html(result.filename)}</strong><br>${frappe.utils.escape_html(result.error)}</div>`);
	}
}

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
				<div class="fel-actions"></div>
				<div class="fel-results"></div>
			</div>
		`);
		this.$files = this.page.main.find(".fel-files");
		this.$actions = this.page.main.find(".fel-actions");
		this.$results = this.page.main.find(".fel-results");
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
				results.push(response.message);
			} catch (error) {
				results.push({ filename: file.name, ok: false, error: error.message || String(error) });
			}
		}
		this.renderResults(results);
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
	}

	documentCard(result) {
		const doc = result.document;
		const matches = result.matches || [];
		const matchHtml = matches.length
			? matches.map((match) => `<li><a href="/app/purchase-invoice/${encodeURIComponent(match.name)}">${frappe.utils.escape_html(match.name)}</a> · ${frappe.utils.escape_html(match.supplier_name || match.supplier || "")} · ${match.currency} ${match.grand_total}</li>`).join("")
			: `<li class="text-muted">${__("Sin coincidencias por NIT, total y moneda")}</li>`;
		const items = (doc.items || []).map((item) => `<tr><td>${item.line_number}</td><td>${frappe.utils.escape_html(item.description)}</td><td>${item.quantity} ${item.unit || ""}</td><td class="text-right">${item.total}</td></tr>`).join("");

		return $(
			`<div class="card mb-3">
				<div class="card-header"><strong>${frappe.utils.escape_html(result.filename)}</strong><span class="indicator-pill green ml-2">${doc.document_type}</span></div>
				<div class="card-body">
					<div class="row">
						${this.field(__("UUID"), doc.uuid, "col-sm-6")}
						${this.field(__("Proveedor"), `${doc.issuer_name} (${doc.issuer_nit})`, "col-sm-6")}
						${this.field(__("Total"), `${doc.currency} ${doc.grand_total}`, "col-sm-3")}
						${this.field(__("Emisión"), doc.emission_datetime, "col-sm-5")}
						${this.field(__("Complementos"), (doc.complements || []).join(", ") || "-", "col-sm-4")}
					</div>
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

frappe.pages["fel-tax-assignment"].on_page_load = function (wrapper) {
	new SatGtFelTaxAssignment(wrapper);
};

class SatGtFelTaxAssignment {
	constructor(wrapper) {
		this.page = frappe.ui.make_app_page({ parent: wrapper, title: __("Asignación de Impuestos FEL"), single_column: true });
		this.render();
		this.load();
	}

	render() {
		this.page.main.html(`
			<div class="fel-tax-assignment">
				<p class="text-muted">${__("Asigna la cuenta contable que se usará al crear borradores desde XML FEL. La asignación es por compañía e impuesto.")}</p>
				<div class="form-row align-items-end">
					<div class="form-group col-sm-4"><label>${__("Compañía")}</label><input class="form-control fel-tax-company" type="text" placeholder="${__("Nombre de la compañía")}"></div>
					<div class="form-group col-sm-3"><label>${__("Impuesto FEL")}</label><input class="form-control fel-tax-name" type="text" placeholder="IVA"></div>
					<div class="form-group col-sm-4"><label>${__("Cuenta contable")}</label><input class="form-control fel-tax-account" type="text" placeholder="${__("Cuenta de IVA")}"></div>
					<div class="form-group col-sm-1"><button class="btn btn-primary fel-tax-save">${__("Guardar")}</button></div>
				</div>
				<div class="fel-tax-list"></div>
			</div>
		`);
		this.$company = this.page.main.find(".fel-tax-company");
		this.$name = this.page.main.find(".fel-tax-name");
		this.$account = this.page.main.find(".fel-tax-account");
		this.$list = this.page.main.find(".fel-tax-list");
		this.page.main.find(".fel-tax-save").on("click", () => this.save());
		this.$company.on("change", () => this.load());
	}

	load() {
		frappe.call({
			method: "sat_gt.sat_gt.page.fel_tax_assignment.fel_tax_assignment.list_mappings",
			args: { company: this.$company.val() || undefined },
		}).then((response) => this.renderList(response.message || []));
	}

	save() {
		frappe.call({
			method: "sat_gt.sat_gt.page.fel_tax_assignment.fel_tax_assignment.save_mapping",
			args: { company: this.$company.val(), tax_name: this.$name.val(), account_head: this.$account.val() },
		}).then(() => {
			frappe.show_alert({ message: __("Asignación guardada"), indicator: "green" });
			this.$name.val("");
			this.$account.val("");
			this.load();
		});
	}

	renderList(rows) {
		if (!rows.length) {
			this.$list.html(`<p class="text-muted">${__("No hay asignaciones configuradas.")}</p>`);
			return;
		}
		this.$list.html(`<table class="table table-bordered"><thead><tr><th>${__("Compañía")}</th><th>${__("Impuesto")}</th><th>${__("Cuenta")}</th><th>${__("Activo")}</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${frappe.utils.escape_html(row.company)}</td><td>${frappe.utils.escape_html(row.tax_name)}</td><td>${frappe.utils.escape_html(row.account_head)}</td><td>${row.enabled ? __("Sí") : __("No")}</td></tr>`).join("")}</tbody></table>`);
	}
}

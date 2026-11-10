frappe.pages["reckon-hrms-run"].on_page_load = function () {
	frappe.route_options = { stage: "run" };
	frappe.set_route("reckon-hrms-setup");
};

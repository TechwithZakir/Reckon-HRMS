frappe.pages["reckon-hrms-company"].on_page_load = function () {
	frappe.route_options = { stage: "company" };
	frappe.set_route("reckon-hrms-setup");
};

frappe.pages["reckon-hrms-salary"].on_page_load = function () {
	frappe.route_options = { stage: "salary" };
	frappe.set_route("reckon-hrms-setup");
};

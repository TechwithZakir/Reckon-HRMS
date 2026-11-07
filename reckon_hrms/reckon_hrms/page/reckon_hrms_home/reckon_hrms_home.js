// Dashboard page: the same KPI dashboard as the Reckon HRMS workspace, drawn by public/hrms/dashboard.js.
frappe.pages["reckon-hrms-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: "Dashboard", single_column: true });
	const root = $(`<div class="rhrms-page"></div>`).appendTo(page.main);
	window.reckonHrmsDashboard.mount(root);
};

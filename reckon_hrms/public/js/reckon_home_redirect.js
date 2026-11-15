// /desk/reckon-hrms is the app's front door: show the Home page there instead of the shortcut cards.
(() => {
	const HOME = ["reckon-hrms", "reckon-hrms-overview"];
	function send_home() {
		const route = frappe.get_route ? frappe.get_route() : [];
		if (route && route.length === 1 && route[0] === "reckon-hrms") frappe.set_route(...HOME);
	}
	$(document).on("page-change", send_home);
	$(document).ready(() => setTimeout(send_home, 300));
})();

frappe.ui.form.on("HRMS Attendance Device", {
	refresh(frm) {
		if (frm.is_new()) return;
		const run = (method, label) =>
			frappe.call({ method: `reckon_hrms.reckon_hrms.doctype.hrms_attendance_device.hrms_attendance_device.${method}`, args: { device: frm.doc.name }, freeze: true, freeze_message: label }).then((r) => {
				const out = r.message || {};
				frappe.msgprint({ title: label, message: frappe.utils.escape_html(out.message || ""), indicator: out.ok ? "green" : "red" });
				frm.reload_doc();
			});
		frm.add_custom_button(__("Test Connection"), () => run("test_connection", __("Testing the connection")));
		frm.add_custom_button(__("Sync Now"), () => run("sync_now", __("Syncing punches")));
		frm.set_intro(__("Pulls check-ins from your ZKBio Time server into Employee Checkin for this company's employees. Match each person with their device code: use the Employee ID, or the Attendance Device ID field on the employee."), "blue");
	},
});

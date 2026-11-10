// Office Location: fill latitude and longitude from the device's current location.
// Stand at the office (or open the form on the office's own device) and press the button.
frappe.ui.form.on("HRMS Office Location", {
	refresh(frm) {
		if (frm.__get_location_btn || !frm.fields_dict.longitude) return;
		frm.__get_location_btn = $(`<button type="button" class="btn btn-default btn-sm" style="margin-top:4px">${__("Get Geo Location")}</button>`)
			.on("click", () => use_current_location(frm));
		frm.fields_dict.longitude.$wrapper.after(frm.__get_location_btn);
	},
});

function use_current_location(frm) {
	if (!navigator.geolocation) {
		frappe.msgprint(__("This device cannot share its location. Type the latitude and longitude by hand."));
		return;
	}
	frappe.show_alert({ message: __("Reading your location..."), indicator: "blue" });
	navigator.geolocation.getCurrentPosition(
		(pos) => {
			const { latitude, longitude, accuracy } = pos.coords;
			frm.set_value("latitude", Number(latitude.toFixed(6)));
			frm.set_value("longitude", Number(longitude.toFixed(6)));
			frappe.show_alert({ message: __("Location set. Accuracy about {0} m.", [Math.round(accuracy)]), indicator: "green" });
		},
		(err) => {
			const reason = err.code === 1
				? __("Location access was refused. Allow it in the browser settings and try again.")
				: __("The location could not be read. Try again outdoors or type the coordinates by hand.");
			frappe.msgprint({ title: __("Location not set"), message: reason, indicator: "red" });
		},
		{ enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
	);
}

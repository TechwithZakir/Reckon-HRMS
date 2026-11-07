from frappe.model.document import Document


class HRMSOfficeLocation(Document):
    def validate(self):
        if not (-90 <= (self.latitude or 0) <= 90 and -180 <= (self.longitude or 0) <= 180):
            from frappe import throw, _

            throw(_("Enter a valid latitude (-90 to 90) and longitude (-180 to 180)."))
        if (self.radius_m or 0) <= 0:
            self.radius_m = 150

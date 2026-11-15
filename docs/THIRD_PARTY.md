# Third-party code

## ZKTeco Checkin Sync (MIT)

The biometric device sync (`reckon_hrms/device_sync.py` and the HRMS Attendance Device doctype) is adapted from
**ZKTeco Checkin Sync** by DeliveryDevs-ERP, https://github.com/DeliveryDevs-ERP/Zkteco-Checkins-Sync, released under the
MIT licence:

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
> documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
> rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright
> notice and this permission notice shall be included in all copies or substantial portions of the Software.
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

What changed for Reckon HRMS: one device per company instead of one site-wide setting, employees matched inside the
device's own company only, the server refuses to connect to private or internal addresses, passwords and tokens are
stored encrypted, each device is queued as its own background job, and the device's authorisation scheme and pages are
handled.

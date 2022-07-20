# IND Appointment Check

## Are you tired of having an appointment scheduled in 2 months?

This script allows you to query the IND API and find the earliest appointment possible.
It will check every 5 seconds, which will usually guarantee you an appointment the very next day if someone cancels.

If the script finds an appointment before your desired appointment date, it will beep.

(Keep in mind this only checks for available appointments, you have to book it yourself)


This script requires the `requests` library for python. Use `pip install requests` to install. Tested on python3.10.

---
© Vadim Isakov, Nick Veld, Ilya Kotelnikov


Licensed under the [GNU General Public License](LICENSE)

import ctypes
import datetime
import json
import os
import platform
import ssl
import re
import time
import urllib.request
import warnings


class ExternalResourceHasChanged(Warning):
    """Something has been changed on the IND resource"""


POSSIBLE_LOCATION_LIST = [
    'AM',
    'DH',
    'RO',
    'UT',
    'ZW',
    'DB',
    'fa24ccf0acbc76a7793765937eaee440',  # lol
    '6b425ff9f87de136a36b813cccf26e23', # Haarlem
]
POSSIBLE_APPOINTMENT_TYPE_LIST = [
    'DOC',
    'BIO',
    'VAA',
    'TKV',
]


def get(location: str, appointment_type: str, num_people: str, date: str) -> str:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    # Not f-string because in such manner
    # it is easier to copy the template into the browser address line
    url = 'https://oap.ind.nl/oap/api/desks/{}/slots/?productKey={}&persons={}'.format(
        location, appointment_type, num_people,
    )
    print('Requesting', url)
    with urllib.request.urlopen(url, context=ssl_context) as web_content:
        response = web_content.read()
    response = response[6:]  # Some closing brackets are returned in the start of the response

    js = json.loads(response)
    try:
        js = js['data']
    except KeyError:
        raise ExternalResourceHasChanged(
            'The IND resource is totally different, no "data" in the response.'
        )
    if not isinstance(js, list):
        raise ExternalResourceHasChanged('The IND resource has changed the data scheme.')
    if not js:
        warnings.warn(
            'There is no appointment slots at all. It is very suspicious.'
            ' But it can be a temporary problem',
            category=ExternalResourceHasChanged,
        )
        return ''
    earliest_appointment_info = js[0]
    try:
        earliest_date = earliest_appointment_info['date']
    except KeyError:
        raise ExternalResourceHasChanged('The IND resource has changed the appointment scheme.')
    earliest_time = earliest_appointment_info['startTime']

    if (
            datetime.datetime.strptime(earliest_date, '%Y-%m-%d')
            < datetime.datetime.strptime(date, '%d-%m-%Y')
    ):
        return earliest_date
    else:
        earliest_datetime = earliest_date + ' ' + earliest_time
        print(
            'Earliest appointment for ' + appointment_type + ' at ' + location
            + ' for ' + num_people + ' person(s) on: ' + earliest_datetime
        )
        return ""


def get_location() -> str:
    regex = '^[1-8]$'

    print('Which desk do you need?')
    print('1. Amsterdam')
    print('2. Den Haag')
    print('3. Rotterdam')
    print('4. Utrecht')
    print('5. Zwolle')
    print('6. Den Bosch')
    print('7. Expatcenter Utrecht')
    print('8. Haarlem')
    location = input()
    while not re.match(regex, location):
        print('invalid appointment location, try again')
        location = input()

    result = POSSIBLE_LOCATION_LIST[int(location) - 1]
    return result


def get_type() -> str:
    regex = '^[1-4]$'

    print('What kind of appointment do you want to make?')
    print('1. Collecting your residence document, registration card or original document')
    print('2. Biometric information (passport photo, fingerprints and signature)')
    print('3. Residence endorsement sticker')
    print('4. Return visa')
    appointment_type = input()

    while not re.match(regex, appointment_type):
        print('invalid appointment type, try again')
        appointment_type = input()

    result = POSSIBLE_APPOINTMENT_TYPE_LIST[int(appointment_type) - 1]
    return result


def get_num_people() -> str:
    print('How many people?')
    num_people = input()
    while not re.match('^[1-6]$', num_people):
        print('max 6 people, try again')
        num_people = input()

    return num_people


def get_date() -> str:
    # thanks https://stackoverflow.com/questions/4709652/python-regex-to-match-dates
    regex = '^([1-9]|0[1-9]|1[0-9]|2[0-9]|3[0-1])-([1-9]|0[1-9]|1[0-2])-([2-9][0-9][0-9][0-9])$'

    print('Before which date would you like to have the appointment? (dd-mm-yyyy)')
    appointment_date = input()
    while not re.match(regex, appointment_date):
        print('invalid date, format is dd-mm-yyyy')
        appointment_date = input()

    return appointment_date


def main() -> None:
    print('|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|')
    print('|                    IND Appointment Checker                   |')
    print('|       by Iaotle, NickVeld, iikotelnikov, and Mitul Shah      |')
    print('|______________________________________________________________|')

    location = get_location()
    appointment_type = get_type()
    num_people = get_num_people()
    date = get_date()

    print(
        'Got it, looking for appointments for'
        f' {appointment_type} at {location} for {num_people} person(s)'
    )

    while True:
        result = get(location, appointment_type, num_people, date)
        if result:
            notification_content = (
                'You can now book an appointment for'
                f' {appointment_type} at {location} for {num_people} person(s) on {result}'
            )
            notification_title = 'Slot available: {result} !'

            print(notification_content)  # Application execution history + fallback

            if platform.system() == 'Windows':
                ctypes.windll.user32.MessageBoxW(0, notification_title, notification_content, 1)
                break
            elif platform.system() == 'Darwin':
                os.system(
                    "osascript -e 'Tell application \"System Events\""
                    f" to display dialog \"{notification_content}\""
                    f" with title \"{notification_title}\"'"
                )
                break
            else:
                # should probably figure out the way to print system messages on Linux
                break
        time.sleep(5)


if __name__ == '__main__':
    main()

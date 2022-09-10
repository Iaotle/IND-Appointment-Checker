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
from typing import List


class ExternalResourceHasChanged(Warning):
    """Something has been changed on the IND resource"""


MAX_PEOPLE_NUMBER = 6

IND_WEBSITE_LOCATION_NAME_LIST = [
    'IND Amsterdam',
    'IND Den Haag',
    'IND Zwolle',
    'IND Den Bosch',
]
IND_WEBSITE_LOCATION_CODE_LIST = [
    'AM',
    'DH',
    'ZW',
    'DB',
]
assert len(IND_WEBSITE_LOCATION_NAME_LIST) == len(IND_WEBSITE_LOCATION_CODE_LIST), (
    f'{len(IND_WEBSITE_LOCATION_NAME_LIST)} == {len(IND_WEBSITE_LOCATION_CODE_LIST)} is not true'
)
IND_WEBSITE_AUX_LOCATION_NAME_LIST = [
    'IND Rijswijk (Collection)',
    'IND Haarlem (Biometrics)',
    'IND Brabanthallen - Den Bosch (Endorsement sticker)',
    'IND Rotterdam (Removed?)',
    'IND Utrecht (Removed?)',
    'Expatcenter Utrecht (Always no slots?)',
]
IND_WEBSITE_AUX_LOCATION_CODE_LIST = [
    'e1afaa1ca15c1778e972efb79ce63633',
    '6b425ff9f87de136a36b813cccf26e23',
    '87d19bfc2e1b572ac3aab17032ed11dc',
    'RO',
    'UT',
    'fa24ccf0acbc76a7793765937eaee440',
]
assert len(IND_WEBSITE_AUX_LOCATION_NAME_LIST) == len(IND_WEBSITE_AUX_LOCATION_CODE_LIST), (
    f'{len(IND_WEBSITE_AUX_LOCATION_NAME_LIST)} == {len(IND_WEBSITE_AUX_LOCATION_CODE_LIST)}'
    ' is not true'
)
EXTERNAL_WEBSITE_LOCATION_NAME_LIST = [
    'Expatcenter Rotterdam ( https://rotterdamexpatcentre.nl/appointment/ind-appointment/ )',
]
EXTERNAL_WEBSITE_LOCATION_CODE_LIST = [
    'https://calendly.com/api/booking/event_types/{appointment_type}/calendar/range'
    '?timezone=Europe%2FBerlin&embed_domain=rotterdamexpatcentre.nl'
    '&range_start={date_range_start}&range_end={date_range_end}',
]
assert len(EXTERNAL_WEBSITE_LOCATION_NAME_LIST) == len(EXTERNAL_WEBSITE_LOCATION_CODE_LIST), (
    f'{len(EXTERNAL_WEBSITE_LOCATION_NAME_LIST)} == {len(EXTERNAL_WEBSITE_LOCATION_CODE_LIST)}'
    ' is not true'
)

APPOINTMENT_TYPE_NAME_LIST = [
    'Collecting your residence document, registration card or original document',
    'Biometric information (passport photo, fingerprints and signature)',
    'Residence endorsement sticker',
    'Return visa',
]
APPOINTMENT_TYPE_CODE_LIST = [
    'DOC',
    'BIO',
    'VAA',
    'TKV',
]
assert len(APPOINTMENT_TYPE_NAME_LIST) == len(APPOINTMENT_TYPE_CODE_LIST), (
    f'{len(APPOINTMENT_TYPE_NAME_LIST)} == {len(APPOINTMENT_TYPE_CODE_LIST)}'
    ' is not true'
)

IND_DATE_FORMAT = '%Y-%m-%d'
INPUT_DATE_FORMAT = '%d-%m-%Y'


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
            datetime.datetime.strptime(earliest_date, IND_DATE_FORMAT)
            < datetime.datetime.strptime(date, INPUT_DATE_FORMAT)
    ):
        return earliest_date
    else:
        earliest_datetime = earliest_date + ' ' + earliest_time
        print(
            'Earliest appointment for ' + appointment_type + ' at ' + location
            + ' for ' + num_people + ' person(s) on: ' + earliest_datetime
        )
        return ""


def print_user_possible_choices(option_list: List[str], first_number_for_input: int = 1) -> None:
    for index, location_name in enumerate(option_list, first_number_for_input):
        print(f'{index}. {location_name}')


def get_input_number(max_number_for_input: int) -> int:
    """Asks user for the right number input if it is wrong

    :param max_number_for_input: number in user input must not exceed this value
    :return: The integer number based on user's input
    """
    index = int(input())
    while not(1 <= index <= max_number_for_input):
        print(f'invalid number (it must be between 1 and {max_number_for_input}, try again')
        index = int(input())
    return index


def get_location() -> str:
    current_max_location_number = 0

    print('Which desk do you need?')
    print_user_possible_choices(
        IND_WEBSITE_LOCATION_NAME_LIST, current_max_location_number + 1,
    )
    current_max_location_number += len(IND_WEBSITE_LOCATION_NAME_LIST)

    print(
        'The following locations can perform not operations/be removed from the official site'
        ' so they can not work or show no free slots'
    )
    print_user_possible_choices(
        IND_WEBSITE_AUX_LOCATION_NAME_LIST, current_max_location_number + 1,
    )
    current_max_location_number += len(IND_WEBSITE_AUX_LOCATION_NAME_LIST)

    location_index = get_input_number(current_max_location_number) - 1

    if location_index > len(IND_WEBSITE_LOCATION_CODE_LIST):
        location_index -= len(IND_WEBSITE_LOCATION_CODE_LIST)
        result = IND_WEBSITE_AUX_LOCATION_CODE_LIST[location_index]
    else:
        result = IND_WEBSITE_LOCATION_CODE_LIST[location_index]
    return result


def get_type() -> str:
    current_max_appointment_type_number = 0

    print('What kind of appointment do you want to make?')
    print_user_possible_choices(APPOINTMENT_TYPE_NAME_LIST, 1)
    current_max_appointment_type_number += len(APPOINTMENT_TYPE_CODE_LIST)

    appointment_type_index = get_input_number(current_max_appointment_type_number) - 1

    result = APPOINTMENT_TYPE_CODE_LIST[appointment_type_index]
    return result


def get_num_people() -> str:
    print('How many people?')

    num_people = get_input_number(MAX_PEOPLE_NUMBER)

    return str(num_people)


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

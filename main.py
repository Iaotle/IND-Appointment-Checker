import calendar
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
from typing import List, Tuple

try:
    import winsound
    raise ImportError()
except ImportError:  # Maybe it cannot be imported on other systems
    if platform.system() == 'Windows':
        warnings.warn(
            "There will not be any notification sound:"
            "package for the notification sound cannot be imported!",
            category=RuntimeWarning,
        )

        class DummyWinSound:
            def MessageBeep(*args, **kwargs): pass

        winsound = DummyWinSound()


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

CALENDLY_API_RESOURCE_PATH = 'https://calendly.com/api/booking/'
IND_API_URL_TEMPLATE = 'https://oap.ind.nl/oap/api/desks/{}/slots/?productKey={}&persons={}'

IND_DATE_FORMAT = '%Y-%m-%d'
INPUT_DATE_FORMAT = '%Y-%m-%d'


def url_generation(
        location: str, appointment_type: str, num_people: str,
        date: str, date_object: datetime.datetime,
) -> str:
    if location.startswith('http'):
        if num_people != '1':
            raise NotImplementedError(
                'For now the search for only one person is implemented for this location'
            )

        if location.startswith(CALENDLY_API_RESOURCE_PATH):
            if appointment_type == 'DOC':
                appointment_type = '3392b90f-9bd5-49e0-9287-b98b8f571286'
            elif appointment_type == 'BIO':
                appointment_type = '449e482a-55b0-4bb4-972e-0dadc4361150'
            elif appointment_type == 'VAA':
                appointment_type = 'd255af53-075d-4e6b-93a7-574410220d88'
            else:
                raise ValueError('This type of appointment is not provided by this location')

            print(
                'NOTE: Only the range from the first to the last day'
                ' of the month you typed will be watched'
            )
            (first_day, last_day) = calendar.monthrange(date_object.year, date_object.month)
            if INPUT_DATE_FORMAT.endswith('-%d'):
                month_str = date[:-2]  # Day representation of '-%d' is two-symbol long
                # The format string adds leading zero if it is necessary
                date_range_start = month_str + '{:0>2}'.format(first_day)
                date_range_end = month_str + '{:0>2}'.format(last_day)
            else:
                raise NotImplementedError(
                    'In order this location can be requested a developer must change date range selection'
                )
        else:
            raise NotImplementedError(
                'In order this location can be requested a developer must add input processing for it'
            )

        url = location.format(
            appointment_type=appointment_type, date_range_start=date_range_start, date_range_end=date_range_end
        )
    else:
        # Not f-string because in such manner
        # it is easier to copy the template into the browser address line
        url = IND_API_URL_TEMPLATE.format(
            location, appointment_type, num_people,
        )

    return url


def parse_response(response: str, location: str) -> Tuple[str, str]:
    if location.startswith(CALENDLY_API_RESOURCE_PATH):
        check_this_slot_is_available = lambda slot: slot['status'] == 'available'
        data_list_key = 'days'
        day_info_key = 'date'
        slot_list_key = 'spots'
        start_time_key = 'start_time'
    else:
        check_this_slot_is_available = lambda slot: True  # Busy slots are not returned
        data_list_key = 'data'
        day_info_key = 'date'
        slot_list_key = ''
        start_time_key = 'startTime'

        # Some closing brackets are returned in the start of the response
        response = response[6:]

    response_parsed_object = json.loads(response)
    try:
        response_parsed_object = response_parsed_object[data_list_key]
    except KeyError:
        raise ExternalResourceHasChanged(
            f'The resource is totally different, no "{data_list_key}" in the response.'
        )

    if not isinstance(response_parsed_object, list):
        raise ExternalResourceHasChanged('The resource has changed the data scheme.')
    if not response_parsed_object:
        warnings.warn(
            'There is no appointment slots at all. It is very suspicious.'
            ' But it can be a temporary problem',
            category=ExternalResourceHasChanged,
        )
        return '', ''

    for appointment_info in response_parsed_object:
        try:
            is_available = check_this_slot_is_available(appointment_info)
        except KeyError:
            raise ExternalResourceHasChanged('The resource has changed an availability info place.')

        if is_available:
            earliest_appointment_info = appointment_info
            break
    else:
        # No available slot
        return '', ''

    try:
        earliest_date = earliest_appointment_info[day_info_key]
    except KeyError:
        raise ExternalResourceHasChanged('The resource has changed the appointment scheme.')

    if location.startswith(CALENDLY_API_RESOURCE_PATH):
        try:
            slot_list = earliest_appointment_info[slot_list_key]
        except KeyError:
            raise ExternalResourceHasChanged('The resource has changed the day info scheme.')

        for appointment_info in slot_list:
            try:
                is_available = check_this_slot_is_available(appointment_info)
            except KeyError:
                raise ExternalResourceHasChanged(
                    'The resource has changed an slot availability info place.'
                )

            if is_available:
                earliest_appointment_info = appointment_info
                break

    try:
        date_string = earliest_appointment_info[start_time_key]
    except KeyError:
        raise ExternalResourceHasChanged('The resource has changed the slot scheme.')

    if location.startswith(CALENDLY_API_RESOURCE_PATH):
        if '+' in date_string:
            date_string = date_string[:date_string.rfind('+')]
        earliest_time = date_string[len(earliest_date) + len('T') + 1:]
    else:
        earliest_time = date_string

    return earliest_date, earliest_time


def get(location: str, appointment_type: str, num_people: str, date: str) -> str:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    date_object = datetime.datetime.strptime(date, INPUT_DATE_FORMAT)

    url = url_generation(location, appointment_type, num_people, date, date_object)

    print('Requesting', url)
    request = urllib.request.Request(
        url, data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }
    )
    with urllib.request.urlopen(request, context=ssl_context) as web_content:
        response = web_content.read()

    earliest_date, earliest_time = parse_response(response, location)
    if earliest_date == '':
        return ''

    if (
            datetime.datetime.strptime(earliest_date, IND_DATE_FORMAT) <= date_object
    ):
        return earliest_date
    else:
        earliest_datetime = earliest_date + ' ' + earliest_time
        print(
            f'Earliest appointment for {appointment_type}'
            f' for {num_people} person(s) is on {earliest_datetime} but it is too late :('
        )
        return ''


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


def get_location() -> Tuple[str, str]:
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

    print(
        'For the following locations the registration is conducted on a separate website'
    )
    print_user_possible_choices(
        EXTERNAL_WEBSITE_LOCATION_NAME_LIST, current_max_location_number + 1,
    )
    current_max_location_number += len(EXTERNAL_WEBSITE_LOCATION_NAME_LIST)

    location_index = get_input_number(current_max_location_number) - 1

    if location_index >= len(IND_WEBSITE_LOCATION_CODE_LIST):
        location_index -= len(IND_WEBSITE_LOCATION_CODE_LIST)
        if location_index >= len(IND_WEBSITE_AUX_LOCATION_CODE_LIST):
            location_index -= len(IND_WEBSITE_AUX_LOCATION_CODE_LIST)
            result = (
                EXTERNAL_WEBSITE_LOCATION_CODE_LIST[location_index],
                EXTERNAL_WEBSITE_LOCATION_NAME_LIST[location_index],
            )
        else:
            result = (
                IND_WEBSITE_AUX_LOCATION_CODE_LIST[location_index],
                IND_WEBSITE_AUX_LOCATION_NAME_LIST[location_index],
            )
    else:
        result = (
            IND_WEBSITE_LOCATION_CODE_LIST[location_index],
            IND_WEBSITE_LOCATION_NAME_LIST[location_index],
        )
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
    regex = '^([2-9][0-9][0-9][0-9])-([1-9]|0[1-9]|1[0-2])-([1-9]|0[1-9]|1[0-9]|2[0-9]|3[0-1])$'

    print('Before which date would you like to have the appointment? (yyyy-mm-dd)')
    appointment_date = input()
    while not re.match(regex, appointment_date):
        print('invalid date, format is yyyy-mm-dd')
        appointment_date = input()

    return appointment_date


def main() -> None:
    print('|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|')
    print('|                    IND Appointment Checker                   |')
    print('|       by NickVeld, Iaotle, iikotelnikov, and Mitul Shah      |')
    print('|______________________________________________________________|')

    location, location_to_print = get_location()
    appointment_type = get_type()
    num_people = get_num_people()
    date = get_date()

    print(
        'Got it, looking for appointments for'
        f' {appointment_type} for {num_people} person(s) at {location_to_print}'
    )

    while True:
        result = get(location, appointment_type, num_people, date)
        if result:
            notification_content = (
                'You can now book an appointment for'
                f' {appointment_type} for {num_people} person(s) on {result} at {location_to_print}'
            )
            notification_title = f'Slot available: {result} !'

            print(notification_content)  # Application execution history + fallback

            if platform.system() == 'Windows':
                winsound.MessageBeep()
                ctypes.windll.user32.MessageBoxW(0, notification_content, notification_title, 1)
            elif platform.system() == 'Darwin':
                os.system(
                    "osascript -e 'Tell application \"System Events\""
                    f" to display dialog \"{notification_content}\""
                    f" with title \"{notification_title}\"'"
                )
            else:
                # TODO: should probably figure out the way to print system messages on other systems
                pass
        time.sleep(5)


if __name__ == '__main__':
    main()

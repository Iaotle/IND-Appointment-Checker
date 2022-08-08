import ctypes
import datetime
import json
import os
import platform
import re
import time
import urllib.request
import warnings
import ssl

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
]
POSSIBLE_APPOINTMENT_TYPE_LIST = [
    'DOC',
    'BIO',
    'VAA',
    'TKV',
]


def get(location: str, appointment_type: str, num_people: str, date: str) -> str:
    myssl = ssl.create_default_context()
    myssl.check_hostname=False
    myssl.verify_mode=ssl.CERT_NONE
    # Not f-string because in such manner
    # it is easier to copy the template into the browser address line
    url = 'https://oap.ind.nl/oap/api/desks/{}/slots/?productKey={}&persons={}'.format(
        location, appointment_type, num_people,
    )
    #  print('Requesting', url)
    with urllib.request.urlopen(url,context=myssl) as web_content:
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
    time = earliest_appointment_info['startTime']

    earliest_date = datetime.datetime.strptime(earliest_date + ' ' + time, '%Y-%m-%d %H:%M')
    date = datetime.datetime.strptime(date, '%d-%m-%Y')

    if (earliest_date < date):
        return str(earliest_date)
    else:
        print("Earliest appointment on " + str(earliest_date), end='\r')
        return ""


def get_location() -> str:
    regex = '^[1-7]$'

    print('Which desk do you need?')
    print('1. Amsterdam')
    print('2. Den Haag')
    print('3. Rotterdam')
    print('4. Utrecht')
    print('5. Zwolle')
    print('6. Den Bosch')
    print('7. Expatcenter Utrecht')
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
    os.system('cls' if os.name == 'nt' else 'clear')
    print('|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|')
    print('|                    IND Appointment Checker                   |')
    print('|             by Iaotle, NickVeld and iikotelnikov             |')
    print('|______________________________________________________________|')

    location = get_location()
    os.system('cls' if os.name == 'nt' else 'clear')
    appointment_type = get_type()
    os.system('cls' if os.name == 'nt' else 'clear')
    num_people = get_num_people()
    os.system('cls' if os.name == 'nt' else 'clear')
    date = get_date()
    os.system('cls' if os.name == 'nt' else 'clear')

    print('Got it, looking for appointments...')

    while True:
        result = get(location, appointment_type, num_people, date)
        if result:
            print('\a')  # makes a beep sound
            if platform.system() == 'Windows':
                ctypes.windll.user32.MessageBoxW(0, result, 'Appointment found on ' + result, 1)
                break
            elif platform.system() == 'Darwin':
                os.system(
                    "osascript -e 'Tell application \"System Events\""
                    + " to display dialog \"Appointment found on "+ result
                    + "\" with title \"Task completed successfully\"'"
                )
                break
            else:
                # should probably figure out the way to print system messages on Linux
                print(f'Appointment found on {result}          ', end='\r')
                # break
        time.sleep(5)


if __name__ == '__main__':
    main()
import requests
import json
import time
import ctypes
import re
import sys


def get(location, type, people, date):
    url = 'https://oap.ind.nl/oap/api/desks/' + location + '/slots/?productKey=' + type + '&persons=' + people
    print(url)
    response = requests.get(url)

    js = json.loads(response.content[6:])
    earliestdate = js['data'][0]['date']
    if earliestdate < date:
        return earliestdate
    else:
        return 0


def get_location():
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

    match int(location):
        case 1:
            location = 'AM'
        case 2:
            location = 'DH'
        case 3:
            location = 'RO'
        case 4:
            location = 'UT'
        case 5:
            location = 'ZW'
        case 6:
            location = 'DB'
        case 7:
            location = 'fa24ccf0acbc76a7793765937eaee440'  # lol

    return location

def get_type():
    regex = '^[1-4]$'

    print('What kind of appointment do you want to make?')
    print('1. Collecting your residence document, registration card or original document')
    print('2. Biometric information (passport photo, fingerprints and signature)')
    print('3. Residence endorsement sticker')
    print('4. Return visa')
    type = input()

    while not re.match(regex, type):
        print('invalid appointment type, try again')
        type = input()
    match int(type):
        case 1:
            type = 'DOC'
        case 2:
            type = 'BIO'
        case 3:
            type = 'VAA'
        case 4:
            type = 'TKV'

    return type

def get_num_people():
    print('How many people?')
    people = input()
    while not re.match('^[1-6]$', people):
        print('max 6 people, try again')
        people = input()

    return people


def get_date():
    # thanks https://stackoverflow.com/questions/4709652/python-regex-to-match-dates
    regex = '^([1-9]|0[1-9]|1[0-9]|2[0-9]|3[0-1])-([1-9]|0[1-9]|1[0-2])-([2-9][0-9][0-9][0-9])$'

    print('Before which date would you like to have the appointment? (dd-mm-yyyy)')
    date = input()
    while not re.match(regex, date):
        print('invalid date, format is dd-mm-yyyy')
        date = input()

    return date

if __name__ == '__main__':
    print('IND Appointment Checker by Iaotle\n')

    location = get_location()
    type = get_type()
    people = get_num_people()
    date = get_date()

    while 1:
        result = get(location, type, people, date)
        if (result):
            ctypes.windll.user32.MessageBoxW(0, result, 'Appointment found on ' + result, 1)
            break
        time.sleep(5)

"""
Configuration constants and default values for the Hungary embassy booking form filler.
"""

from datetime import date, timedelta
import random
import string


def _system_rng():
    """Lazily initialise and reuse a SystemRandom instance."""
    if not hasattr(_system_rng, "_instance"):
        _system_rng._instance = random.SystemRandom()
    return _system_rng._instance


def _random_name():
    rng = _system_rng()
    first_names = [
        # Serbian names
        "Marko",
        "Nikola",
        "Jelena",
        "Mila",
        "Sara",
        "Luka",
        "Stefan",
        "Ana",
        "Ivana",
        "Petar",
        "Milan",
        "Dragan",
        "Zoran",
        "Dejan",
        "Nenad",
        "Bojan",
        "Vladimir",
        "Aleksandar",
        "Milos",
        "Dusan",
        "Jovana",
        "Milica",
        "Tamara",
        "Jasmina",
        "Snezana",
        "Natasa",
        "Marija",
        "Katarina",
        "Aleksandra",
        # Russian names
        "Ivan",
        "Dmitri",
        "Alexander",
        "Sergei",
        "Andrei",
        "Mikhail",
        "Vladimir",
        "Alexei",
        "Nikolai",
        "Pavel",
        "Yuri",
        "Maxim",
        "Anton",
        "Roman",
        "Igor",
        "Elena",
        "Maria",
        "Anna",
        "Olga",
        "Tatiana",
        "Natalia",
        "Svetlana",
        "Irina",
        "Ekaterina",
        "Yulia",
        "Anastasia",
        "Daria",
        "Victoria",
        "Kristina",
        "Marina",
    ]
    last_names = [
        # Serbian surnames
        "Petrovic",
        "Jovanovic",
        "Markovic",
        "Nikolic",
        "Ilic",
        "Kovacevic",
        "Stankovic",
        "Milosevic",
        "Savic",
        "Filipovic",
        "Djordjevic",
        "Pavlovic",
        "Lazic",
        "Stefanovic",
        "Mitic",
        "Radic",
        "Popovic",
        "Tomic",
        "Vukovic",
        "Zivkovic",
        "Simic",
        "Maric",
        "Jankovic",
        "Ristic",
        "Mladenovic",
        "Stojanovic",
        "Bogdanovic",
        "Cvetkovic",
        "Kostic",
        "Djuric",
        # Russian surnames
        "Ivanov",
        "Petrov",
        "Sidorov",
        "Smirnov",
        "Kuznetsov",
        "Popov",
        "Sokolov",
        "Lebedev",
        "Kozlov",
        "Novikov",
        "Morozov",
        "Volkov",
        "Alekseev",
        "Romanov",
        "Orlov",
        "Pavlov",
        "Semenov",
        "Stepanov",
        "Nikolaev",
        "Orlova",
        "Ivanova",
        "Petrova",
        "Sidorova",
        "Smirnova",
        "Kuznetsova",
        "Popova",
        "Sokolova",
        "Lebedeva",
        "Kozlova",
        "Novikova",
    ]
    return f"{rng.choice(first_names)} {rng.choice(last_names)}"


def _random_email(name: str):
    rng = _system_rng()
    handle = name.lower().replace(" ", ".")
    domain = rng.choice(["example.com", "mail.com", "inbox.eu", "test.org"])
    suffix = rng.randint(10, 9999)
    return f"{handle}{suffix}@{domain}"


def _random_phone():
    rng = _system_rng()
    digits = "".join(str(rng.randint(0, 9)) for _ in range(7))
    return f"+361{digits}"


def _random_date_of_birth(start_year=1960, end_year=2002):
    rng = _system_rng()
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    random_days = rng.randint(0, (end - start).days)
    dob = start + timedelta(days=random_days)
    return dob.strftime("%d/%m/%Y"), dob.strftime("%Y-%m-%d")


def _random_passport():
    rng = _system_rng()
    letters = "".join(rng.choice(string.ascii_uppercase) for _ in range(2))
    numbers = "".join(str(rng.randint(0, 9)) for _ in range(6))
    return f"{letters}{numbers}"


def _random_residence_permit():
    rng = _system_rng()
    return "".join(str(rng.randint(0, 9)) for _ in range(9))


def _generate_dynamic_defaults():
    name = _random_name()
    email = _random_email(name)
    phone = _random_phone()
    dob_display, dob_iso = _random_date_of_birth()
    passport = _random_passport()
    residence_permit = _random_residence_permit()
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "date_of_birth": dob_display,
        "date_of_birth_iso": dob_iso,
        "passport": passport,
        "residence_permit": residence_permit,
    }


_DYNAMIC_DEFAULTS = _generate_dynamic_defaults()

# URL Configuration
BOOKING_URL = "https://konzinfobooking.mfa.gov.hu/"

# Default form values
DEFAULT_VALUES = {
    **_DYNAMIC_DEFAULTS,
    "citizenship": "Russian Federation",
    "residential_community": "Novi Sad",
    "applicants": "1",
}

# Field mapping by ID
FIELD_MAP = {
    "label4": ("name", DEFAULT_VALUES["name"]),
    "birthDate": ("date_of_birth", DEFAULT_VALUES["date_of_birth"]),
    "label6": ("applicants", DEFAULT_VALUES["applicants"]),
    "label9": ("phone", DEFAULT_VALUES["phone"]),
    "label10": ("email", DEFAULT_VALUES["email"]),
    "label1000": ("residence_permit", DEFAULT_VALUES["residence_permit"]),
    "label1001": ("citizenship", DEFAULT_VALUES["citizenship"]),
    "label1002": ("passport", DEFAULT_VALUES["passport"]),
    "label1003": ("residential_community", DEFAULT_VALUES["residential_community"]),
    "slabel13": ("checkbox", None),  # First consent checkbox
    "label13": ("checkbox", None),   # Second consent checkbox
}

# Dropdown IDs and options
CONSULATE_DROPDOWN_NAME = "ugyfelszolgalat"
CONSULATE_DROPDOWN_ID = "f05149cd-51b4-417d-912b-9b8e1af999b6"
CONSULATE_OPTION_TEXT = "Serbia - Subotica"

VISA_TYPE_DROPDOWN_ID = "7c357940-1e4e-4b29-8e87-8b1d09b97d07"
VISA_TYPE_OPTION_TEXT = "Visa application (Schengen visa- type 'C')"

# Timing constants (in seconds)
PAGE_LOAD_WAIT = 20
ELEMENT_WAIT_TIME = 0.3
CHAR_TYPE_DELAY = 0.08
SCROLL_WAIT = 0.5
INSPECTION_TIME = 30

# Textarea default value
DEFAULT_TEXTAREA_VALUE = "Test message"


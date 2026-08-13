import json
import re
import random
from datetime import date
from faker import Faker
from typing import Dict
import os

fake = Faker(['en_IN', 'en_US'])
fake_in = Faker('en_IN')
fake_us = Faker('en_US')


def preserve_case(original: str, replacement: str) -> str:
    """Preserves UPPERCASE, lowercase, or Title Case of the original string in the replacement."""
    if original.isupper():
        return replacement.upper()
    elif original.islower():
        return replacement.lower()
    # Check for Title Case
    elif original.istitle():
        return replacement.title()
    return replacement


class Anonymizer:
    def __init__(self, persist_path: str = "output/mapping.json"):
        self.mapping: Dict[str, str] = {}
        self.persist_path = persist_path
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self.mapping = json.load(f)
            except Exception:
                self.mapping = {}

    def save(self):
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

    def fake_for(self, ent_type: str, original: str) -> str:
        # Standardize the type name (e.g. NAME -> PERSON, IP -> IP_ADDRESS)
        std_type = ent_type
        if ent_type == "NAME":
            std_type = "PERSON"
        elif ent_type == "IP":
            std_type = "IP_ADDRESS"

        key = f"{std_type}::{original.strip().lower()}"
        if key in self.mapping:
            return preserve_case(original, self.mapping[key])

        # Generate fake data based on type
        if std_type == "PERSON":
            val = fake.name()
        elif std_type == "EMAIL":
            # Generate email based on faker username or name
            username = fake.simple_profile().get("username", "user")
            val = f"{username}@example.com"
        elif std_type == "PHONE":
            if "+91" in original or any(ch in original for ch in ["Pune", "Bangalore", "India"]):
                # Generate a valid Indian mobile number starting with 6-9
                first = str(random.choice(['6', '7', '8', '9']))
                rest = "".join(str(random.randint(0, 9)) for _ in range(9))
                val = f"+91 {first}{rest}"
            else:
                # Fallback to general phone number
                val = fake.phone_number()
        elif std_type == "COMPANY":
            val = fake.company()
            # If the original ends with a specific suffix, we can append it if not present
            suffixes = ["Private Limited", "Pvt Ltd", "Limited", "Ltd", "Corporation", "Corp", "Inc", "LLP"]
            for suf in suffixes:
                if original.lower().endswith(suf.lower()) and not val.lower().endswith(suf.lower()):
                    val = f"{val} {suf}"
                    break
        elif std_type == "ADDRESS":
            is_indian = any(k in original.lower() for k in ["india", "pune", "bangalore", "mumbai", "maharashtra", "delhi", "chennai", "kolkata"])
            if is_indian:
                val = fake_in.address().replace("\n", ", ")
            else:
                val = fake_us.address().replace("\n", ", ")
        elif std_type == "IP_ADDRESS":
            val = fake.ipv4()
        elif std_type == "SSN":
            val = fake.ssn()
        elif std_type == "CREDIT_CARD":
            val = fake.credit_card_number()
        elif std_type == "DOB":
            # Generate a realistic birth date between 1970 and 2010
            start_date = date(1970, 1, 1).toordinal()
            end_date = date(2010, 12, 31).toordinal()
            random_day = date.fromordinal(random.randint(start_date, end_date))
            
            # Detect separator
            if "/" in original:
                parts = original.split("/")
                if len(parts[0]) == 4:
                    val = random_day.strftime("%Y/%m/%d")
                else:
                    val = random_day.strftime("%d/%m/%Y")
            elif "-" in original:
                parts = original.split("-")
                if len(parts[0]) == 4:
                    val = random_day.strftime("%Y-%m-%d")
                else:
                    val = random_day.strftime("%d-%m-%Y")
            else:
                val = random_day.strftime("%d %B %Y")
        else:
            val = f"REDACTED_{std_type}"

        # Cache key mapping with normalized value
        self.mapping[key] = val
        return preserve_case(original, val)

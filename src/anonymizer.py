import json
from faker import Faker
from typing import Dict
import os

fake = Faker()


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
        key = f"{ent_type}::{original}"
        if key in self.mapping:
            return self.mapping[key]
        if ent_type in ("NAME", "PERSON"):
            val = fake.name()
        elif ent_type in ("EMAIL",):
            # create email based on faker name
            nm = fake.simple_profile().get("username")
            val = f"{nm}@example.com"
        elif ent_type in ("PHONE",):
            val = fake.phone_number()
        elif ent_type in ("COMPANY",):
            val = fake.company()
        elif ent_type in ("ADDRESS",):
            val = fake.address().replace("\n", ", ")
        elif ent_type in ("IP",):
            val = fake.ipv4()
        elif ent_type in ("SSN",):
            val = fake.ssn()
        elif ent_type in ("CREDIT_CARD",):
            val = fake.credit_card_number()
        elif ent_type in ("DATE",):
            val = fake.date()
        else:
            val = f"REDACTED_{ent_type}"
        self.mapping[key] = val
        return val

import json
import re
import random
import os
from datetime import date
from faker import Faker
from typing import Dict

# Unique initialization style for the data generator providers
prov_ind = Faker("en_IN")
prov_usa = Faker("en_US")
prov_mix = Faker(["en_IN", "en_US"])


def maintain_casing_format(original_text: str, generated_text: str) -> str:
    """
    Applies the casing pattern (uppercase, lowercase, title case) 
    found in original_text onto generated_text.
    """
    if original_text.isupper():
        return generated_text.upper()
    if original_text.islower():
        return generated_text.lower()
    if original_text.istitle():
        return generated_text.title()
    return generated_text


class Anonymizer:
    """
    Manages persistent mappings between original PII and generated pseudonyms.
    Uses localized Faker providers for realistic substitutions.
    """
    def __init__(self, persist_path: str = "output/mapping.json"):
        self.storage_file = persist_path
        self.pseudonym_cache: Dict[str, str] = {}
        
        # Load stored pseudonym cache if existing
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as file_stream:
                    self.pseudonym_cache = json.load(file_stream)
            except Exception:
                self.pseudonym_cache = {}

    def save(self) -> None:
        """Serializes current pseudonym cache mappings back to disk."""
        os.makedirs(os.path.dirname(self.storage_file) or ".", exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as file_stream:
            json.dump(self.pseudonym_cache, file_stream, ensure_ascii=False, indent=2)

    def fake_for(self, ent_type: str, original: str) -> str:
        """
        Generates or retrieves a case-preserved pseudonym for a given PII type and value.
        """
        # Map labels to standardized keys
        canonical_label = {
            "NAME": "PERSON",
            "IP": "IP_ADDRESS"
        }.get(ent_type, ent_type)

        cache_key = f"{canonical_label}::{original.strip().lower()}"
        if cache_key in self.pseudonym_cache:
            return maintain_casing_format(original, self.pseudonym_cache[cache_key])

        # Generate fake value based on standardized type
        generated_value = ""
        if canonical_label == "PERSON":
            generated_value = prov_mix.name()
            
        elif canonical_label == "EMAIL":
            user_profile = prov_mix.simple_profile()
            uname = user_profile.get("username", "identity")
            generated_value = f"{uname}@example.com"
            
        elif canonical_label == "PHONE":
            # Direct check for Indian phone criteria
            is_indian_number = "+91" in original or any(term in original for term in ["Pune", "Bangalore", "India"])
            if is_indian_number:
                # Custom Indian cell number generation
                lead_digit = random.choice("6789")
                suffix_digits = "".join(random.choice("0123456789") for _ in range(9))
                generated_value = f"+91 {lead_digit}{suffix_digits}"
            else:
                generated_value = prov_mix.phone_number()
                
        elif canonical_label == "COMPANY":
            generated_value = prov_mix.company()
            corporate_suffixes = ["Private Limited", "Pvt Ltd", "Limited", "Ltd", "Corporation", "Corp", "Inc", "LLP"]
            for suffix in corporate_suffixes:
                if original.lower().endswith(suffix.lower()) and not generated_value.lower().endswith(suffix.lower()):
                    generated_value = f"{generated_value} {suffix}"
                    break
                    
        elif canonical_label == "ADDRESS":
            has_indian_context = any(word in original.lower() for word in ["india", "pune", "bangalore", "mumbai", "maharashtra", "delhi", "chennai", "kolkata"])
            provider = prov_ind if has_indian_context else prov_usa
            generated_value = provider.address().replace("\n", ", ")
            
        elif canonical_label == "IP_ADDRESS":
            generated_value = prov_mix.ipv4()
            
        elif canonical_label == "SSN":
            generated_value = prov_mix.ssn()
            
        elif canonical_label == "CREDIT_CARD":
            generated_value = prov_mix.credit_card_number()
            
        elif canonical_label == "DOB":
            # Random date of birth generation
            start_ord = date(1970, 1, 1).toordinal()
            end_ord = date(2010, 12, 31).toordinal()
            birth_date = date.fromordinal(random.randint(start_ord, end_ord))
            
            # Match separators and format
            if "/" in original:
                parts = original.split("/")
                val_format = "%Y/%m/%d" if len(parts[0]) == 4 else "%d/%m/%Y"
            elif "-" in original:
                parts = original.split("-")
                val_format = "%Y-%m-%d" if len(parts[0]) == 4 else "%d-%m-%Y"
            else:
                val_format = "%d %B %Y"
            generated_value = birth_date.strftime(val_format)
            
        else:
            generated_value = f"REDACTED_{canonical_label}"

        self.pseudonym_cache[cache_key] = generated_value
        return maintain_casing_format(original, generated_value)

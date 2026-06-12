"""
Test: 3-step import — fuzzy column mapping + row validation
Ensures: messy real-world headers auto-map (≥80% confidence), low-confidence
guesses are NOT auto-applied, required-field gaps block the import, and bad
rows get plain-language per-row errors while good rows pass.
"""
import pytest
from fastapi import HTTPException

from app.routers.import_data import (
    ENTITY_FIELDS,
    _apply_mapping_and_validate,
    _clean_phone,
    _coerce,
    _parse_datetime,
    suggest_mapping,
)


class TestFuzzyMapping:
    def test_common_header_variants_auto_map(self):
        spec = ENTITY_FIELDS["patients"]
        for header in ["Patient Name", "patient name", "PatientName", "name of patient"]:
            s = suggest_mapping([header], spec)[header]
            assert s["field"] == "name", f"{header!r} mapped to {s['field']!r}"
            assert s["auto"] is True, f"{header!r} confidence {s['confidence']} not auto-applied"

    def test_phone_variants_auto_map(self):
        spec = ENTITY_FIELDS["patients"]
        for header in ["Phone Number", "Mobile", "WhatsApp", "Contact"]:
            s = suggest_mapping([header], spec)[header]
            assert s["field"] == "phone"
            assert s["auto"] is True

    def test_unrelated_header_not_auto_applied(self):
        spec = ENTITY_FIELDS["patients"]
        s = suggest_mapping(["Favourite Cricket Team"], spec)["Favourite Cricket Team"]
        assert s["auto"] is False, \
            f"nonsense header auto-mapped to {s['field']} at {s['confidence']}%"


class TestValueValidation:
    def test_pakistani_phone_normalized(self):
        assert _clean_phone("0300-1234567") == "03001234567"
        assert _clean_phone("+92 300 1234567") == "03001234567"
        assert _clean_phone("923001234567") == "03001234567"

    def test_bad_phone_rejected(self):
        assert _clean_phone("12345") is None
        assert _clean_phone("abc") is None

    def test_date_formats(self):
        assert _parse_datetime("2026-06-15 10:30") is not None
        assert _parse_datetime("15/06/2026 10:30") is not None
        assert _parse_datetime("15-06-2026 10:30 AM") is not None
        assert _parse_datetime("yesterday-ish") is None

    def test_coerce_int(self):
        assert _coerce("42", "int", "Age") == (42, None)
        value, err = _coerce("forty", "int", "Age")
        assert value is None and "Age" in err


class TestRowValidation:
    SPEC = ENTITY_FIELDS["patients"]
    HEADERS = ["Full Name", "Mobile", "Age"]
    MAPPING = {"Full Name": "name", "Mobile": "phone", "Age": "age"}

    def test_valid_rows_pass(self):
        rows = [["Ali Raza", "03001234567", "30"]]
        valid, errors = _apply_mapping_and_validate(self.HEADERS, rows, self.MAPPING, self.SPEC)
        assert len(valid) == 1 and not errors
        assert valid[0] == {"name": "Ali Raza", "phone": "03001234567", "age": 30}

    def test_bad_rows_reported_with_row_numbers(self):
        rows = [
            ["Ali Raza", "03001234567", "30"],   # row 2 — ok
            ["Sara Khan", "not-a-phone", "x"],   # row 3 — two errors
            ["", "03007654321", ""],             # row 4 — missing name
        ]
        valid, errors = _apply_mapping_and_validate(self.HEADERS, rows, self.MAPPING, self.SPEC)
        assert len(valid) == 1
        assert {e["row"] for e in errors} == {3, 4}
        row3 = next(e for e in errors if e["row"] == 3)
        assert len(row3["errors"]) == 2

    def test_unmapped_required_field_blocks_import(self):
        with pytest.raises(HTTPException) as exc:
            _apply_mapping_and_validate(
                self.HEADERS, [["Ali", "03001234567", "30"]],
                {"Full Name": "name"},  # phone (required) not mapped
                self.SPEC,
            )
        assert "Phone Number" in exc.value.detail

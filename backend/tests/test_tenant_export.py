"""
Test: per-clinic data export.
The CSV/ZIP builder must serialise cells safely, never export secret columns,
and produce a ZIP containing one CSV per table plus a manifest.
"""
import io
import json
import zipfile

from app.models.chat import ChatSession
from app.services.tenant_export import _cell, _rows_to_csv, build_tenant_export_zip, _TABLES


class TestCell:
    def test_none_is_empty(self):
        assert _cell(None) == ""

    def test_dict_and_list_become_json(self):
        assert json.loads(_cell({"a": 1})) == {"a": 1}
        assert json.loads(_cell([1, 2])) == [1, 2]

    def test_scalar_stringified(self):
        assert _cell(42) == "42"


class TestRowsToCsv:
    def test_secret_columns_excluded(self):
        # ChatSession has session_token — it must not appear in the export header.
        csv_text = _rows_to_csv(ChatSession, [])
        header = csv_text.splitlines()[0]
        assert "session_token" not in header
        assert "patient_name" in header

    def test_internal_tenant_id_excluded_but_id_kept(self):
        # tenant_id is dropped as internal noise; row id stays (needed for joins).
        header = _rows_to_csv(ChatSession, []).splitlines()[0].split(",")
        assert "tenant_id" not in header
        assert "id" in header


# Minimal fake DB so we can assert the ZIP shape without a real database.
class _FakeQuery:
    def filter(self, *a, **k): return self
    def all(self): return []


class _FakeDB:
    def query(self, *a, **k): return _FakeQuery()


class TestBuildZip:
    def test_zip_has_every_table_and_readme(self):
        zip_bytes, counts = build_tenant_export_zip(_FakeDB(), "tenant-1")
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        names = set(zf.namelist())
        for filename, _model in _TABLES:
            assert filename in names
        assert "README.txt" in names
        assert all(v == 0 for v in counts.values())

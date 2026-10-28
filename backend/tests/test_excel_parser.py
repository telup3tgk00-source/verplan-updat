"""
test_excel_parser.py — Unit test untuk fungsi parse_excel_file di upload.py
Test ini men-unit-test logika parsing tanpa menyentuh DB/HTTP.
"""

import io
import pytest
import openpyxl


def make_excel(headers, rows):
    """Helper untuk membuat bytes Excel."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


class TestParseExcelFile:
    """Test fungsi parse_excel_file secara terisolasi."""

    def _parse(self, file_bytes, record_type="beda", session_id=1):
        """Import dan jalankan parser."""
        from app.routers.upload import parse_excel_file
        return parse_excel_file(file_bytes, record_type, session_id)

    # ─── Happy Path ────────────────────────────────────────────────────────────

    def test_parse_valid_match_file(self, valid_match_excel):
        """File valid dengan 2 baris harus menghasilkan 2 record."""
        records = self._parse(valid_match_excel, "match")
        assert len(records) == 2
        # Semua record match harus langsung VERIFIED_OK
        from app.models import StatusEnum
        for r in records:
            assert r.status == StatusEnum.VERIFIED_OK

    def test_parse_valid_beda_file(self, valid_beda_excel):
        """File BEDA dengan 2 baris harus menghasilkan 2 record PENDING."""
        records = self._parse(valid_beda_excel, "beda")
        assert len(records) == 2
        from app.models import StatusEnum
        for r in records:
            assert r.status == StatusEnum.PENDING

    def test_parse_record_type_stored(self, valid_match_excel, valid_beda_excel):
        """record_type harus tersimpan sesuai parameter."""
        match_records = self._parse(valid_match_excel, "match")
        beda_records = self._parse(valid_beda_excel, "beda")
        for r in match_records:
            assert r.record_type == "match"
        for r in beda_records:
            assert r.record_type == "beda"

    # ─── Column Name Variants ──────────────────────────────────────────────────

    def test_parse_idpel_column_variants(self):
        """Parser harus mengenali berbagai nama kolom ID Pelanggan."""
        variants = ["ID Pelanggan", "IDPEL", "No Pelanggan", "id_pelanggan"]
        for col_name in variants:
            excel = make_excel(
                [col_name, "Stand AI", "Stand Biller"],
                [["123456789001", 1500, 1500]]
            )
            records = self._parse(excel)
            assert len(records) == 1, f"Kolom '{col_name}' tidak dikenali"
            assert records[0].id_pelanggan == "123456789001"

    def test_parse_stand_column_variants(self):
        """Parser harus mengenali berbagai nama kolom Stand."""
        excel = make_excel(
            ["ID Pelanggan", "KWH AI", "stand_baca"],
            [["IDPEL001", 1500, 1000]]
        )
        records = self._parse(excel)
        assert len(records) == 1
        assert records[0].stand_ai == 1500
        assert records[0].stand_petugas == 1000

    # ─── Edge Cases ───────────────────────────────────────────────────────────

    def test_parse_no_idpel_column_raises(self):
        """Excel tanpa kolom ID Pelanggan harus raise ValueError."""
        excel = make_excel(
            ["Stand AI", "Stand Biller", "Selisih"],
            [[1500, 1500, 0]]
        )
        with pytest.raises(ValueError, match="ID Pelanggan"):
            self._parse(excel)

    def test_parse_empty_rows_skipped(self, empty_excel):
        """Baris kosong (hanya header) harus menghasilkan 0 record."""
        records = self._parse(empty_excel)
        assert len(records) == 0

    def test_parse_nan_idpel_skipped(self):
        """Baris dengan ID Pelanggan 'nan' atau kosong harus dilewati."""
        excel = make_excel(
            ["ID Pelanggan", "Stand AI", "Stand Biller"],
            [
                [None, 1500, 1500],   # None ID
                ["nan", 1000, 1000],  # string 'nan'
                ["   ", 500, 500],    # spasi saja
                ["VALID001", 200, 200],  # valid
            ]
        )
        records = self._parse(excel)
        # Hanya VALID001 yang lolos
        assert len(records) == 1
        assert records[0].id_pelanggan == "VALID001"

    def test_parse_anomaly_detection(self):
        """Selisih > 500 harus ditandai sebagai anomaly."""
        excel = make_excel(
            ["ID Pelanggan", "Stand AI", "Stand Biller", "Selisih"],
            [
                ["NORMAL001", 1500, 1450, 50],    # Normal
                ["ANOMALY001", 10000, 100, 9900],  # Anomali!
            ]
        )
        records = self._parse(excel)
        assert len(records) == 2
        normal = next(r for r in records if r.id_pelanggan == "NORMAL001")
        anomaly = next(r for r in records if r.id_pelanggan == "ANOMALY001")
        assert normal.is_anomaly is False
        assert anomaly.is_anomaly is True

    def test_parse_selisih_calculated_if_missing(self):
        """Selisih harus dihitung otomatis jika kolom tidak ada."""
        excel = make_excel(
            ["ID Pelanggan", "Stand AI", "Stand Biller"],  # Tidak ada kolom Selisih
            [["CALC001", 1500, 1000]]
        )
        records = self._parse(excel)
        assert len(records) == 1
        assert records[0].selisih == 500.0  # abs(1500 - 1000)

    def test_parse_invalid_float_values(self):
        """Nilai stand yang tidak bisa dikonversi ke float harus dihandle (None)."""
        excel = make_excel(
            ["ID Pelanggan", "Stand AI", "Stand Biller"],
            [["BADVAL001", "RUSAK", "JUGA_RUSAK"]]
        )
        records = self._parse(excel)
        assert len(records) == 1
        assert records[0].stand_ai is None
        assert records[0].stand_petugas is None

    def test_parse_session_id_assigned(self):
        """Semua record harus memiliki session_id yang benar."""
        excel = make_excel(
            ["ID Pelanggan", "Stand AI"],
            [["TEST001", 1000], ["TEST002", 2000]]
        )
        records = self._parse(excel, session_id=42)
        for r in records:
            assert r.session_id == 42

    def test_parse_merek_and_tipe_columns(self):
        """Kolom Merek dan Tipe harus ter-parse dengan benar."""
        excel = make_excel(
            ["ID Pelanggan", "Stand AI", "Stand Biller", "Merek", "Tipe Stan"],
            [["MEREK001", 1000, 1000, "ITRON", "1P"]]
        )
        records = self._parse(excel)
        assert len(records) == 1
        assert records[0].merek_ai == "ITRON"
        assert records[0].tipe_ai == "1P"

    def test_parse_large_dataset(self):
        """Parser harus bisa menangani file dengan banyak baris tanpa error."""
        headers = ["ID Pelanggan", "Stand AI", "Stand Biller"]
        rows = [[f"IDPEL{i:06d}", 1000 + i, 1000 + i] for i in range(2000)]
        excel = make_excel(headers, rows)
        records = self._parse(excel)
        assert len(records) == 2000


class TestSafeFloat:
    def test_safe_float_valid_number(self):
        from app.routers.upload import safe_float
        assert safe_float(1500) == 1500.0
        assert safe_float("1500.5") == 1500.5
        assert safe_float(0) == 0.0

    def test_safe_float_none(self):
        from app.routers.upload import safe_float
        assert safe_float(None) is None

    def test_safe_float_nan_string(self):
        import pandas as pd
        from app.routers.upload import safe_float
        assert safe_float(float("nan")) is None

    def test_safe_float_invalid_string(self):
        from app.routers.upload import safe_float
        assert safe_float("TIDAK_VALID") is None
        assert safe_float("abc") is None

    def test_safe_float_empty_string(self):
        from app.routers.upload import safe_float
        assert safe_float("") is None

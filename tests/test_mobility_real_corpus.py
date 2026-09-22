"""Optional local integration checks against the user's DOI-organized corpus.

These tests are skipped on machines without D:/papers/data or pdfplumber. They
store only DOI filenames, page numbers, and expected normalized facts; no paper
text is copied into the repository.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mobility_miner.extract import extract_mobility_fields


PDFPLUMBER_AVAILABLE = importlib.util.find_spec("pdfplumber") is not None
DATA_ROOT = Path("D:/papers/data")


@unittest.skipUnless(PDFPLUMBER_AVAILABLE and DATA_ROOT.is_dir(), "local mobility PDF corpus unavailable")
class RealMobilityCorpusTests(unittest.TestCase):
    @staticmethod
    def extract_page(relative_path: str, page_number: int):
        import pdfplumber

        path = DATA_ROOT / relative_path
        if not path.is_file():
            raise unittest.SkipTest("missing corpus PDF: {}".format(path))
        with pdfplumber.open(str(path)) as pdf:
            text = " ".join((pdf.pages[page_number - 1].extract_text() or "").split())
        fields = extract_mobility_fields(text)
        if fields is None:
            return []
        return fields.get("mobilities", [])

    def test_uio66_deformation_potential_result(self):
        measurements = self.extract_page("MOF/10.1007_s11664-018-6220-y.pdf", 18)

        self.assertTrue(
            any(item.get("value") == 0.0014 and item.get("standard_units") == "cm^2 V^-1 s^-1" for item in measurements)
        )

    def test_perovskite_optp_range_and_uncertainty(self):
        measurements = self.extract_page("PVSK/10.1002_adfm.201902656.pdf", 7)

        self.assertTrue(any(item.get("value_range") == [13.0, 15.0] for item in measurements))
        self.assertTrue(any(item.get("value") == 3.0 and item.get("uncertainty") == 1.0 for item in measurements))
        self.assertTrue(any("terahertz spectroscopy" in item.get("methods", []) for item in measurements))

    def test_cof_trts_value(self):
        measurements = self.extract_page("COF/10.1038_s41467-026-77017-x.pdf", 4)

        matching = [item for item in measurements if item.get("value") == 200.0]
        self.assertTrue(matching)
        self.assertIn("terahertz spectroscopy", matching[0].get("methods", []))
        self.assertEqual("mobility_yield_product", matching[0].get("quantity_kind"))
        self.assertEqual(
            "lower_bound_of_true_mobility",
            matching[0].get("mobility_relation", {}).get("relation"),
        )

    def test_osm_single_crystal_fet_regime_values(self):
        measurements = self.extract_page("OSM/10.1038_ncomms1451.pdf", 5)

        saturation = [item for item in measurements if item.get("value") == 12.3]
        linear = [item for item in measurements if item.get("value") == 16.0]
        self.assertTrue(saturation)
        self.assertTrue(linear)
        self.assertIn("field-effect transistor", saturation[0].get("methods", []))
        self.assertIn("field-effect transistor", linear[0].get("methods", []))
        self.assertTrue(any(item.get("measurement_regime", {}).get("regime") == "saturation" for item in saturation))
        self.assertTrue(any(item.get("measurement_regime", {}).get("regime") == "linear" for item in linear))


if __name__ == "__main__":
    unittest.main()

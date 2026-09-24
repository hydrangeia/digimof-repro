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

    def test_uio66_record_binds_material_algorithm_and_evidence(self):
        try:
            from mobility_miner.sources import parse_pdf_path
        except ImportError as error:
            raise unittest.SkipTest("mobility source dependencies unavailable: {}".format(error))

        path = DATA_ROOT / "MOF/10.1007_s11664-018-6220-y.pdf"
        records = [
            record
            for record in parse_pdf_path(path, pages=18)
            if record["source"].get("page") == 18
        ]
        matches = [
            (record, measurement)
            for record in records
            for measurement in record.get("fields", {}).get("mobilities", [])
            if measurement.get("value") == 0.0014
        ]

        self.assertEqual(1, len(matches))
        record, measurement = matches[0]
        self.assertEqual("computational", measurement["determination"])
        self.assertEqual(
            ["deformation-potential theory"],
            measurement["algorithms"],
        )
        self.assertEqual(
            "deformation)potential",
            measurement["algorithm_evidence"][0]["raw_text"],
        )
        self.assertEqual([0], measurement["material_refs"])
        self.assertEqual(
            "UiO-66(Hf5Zr1)-BDC",
            record["fields"]["materials"][0]["material"],
        )
        material = next(
            condition
            for condition in measurement["condition_records"]
            if condition["field"] == "material_identity"
        )
        self.assertEqual("UiO-66(Hf5Zr1)-BDC", material["value"])
        self.assertEqual(18, material["evidence_refs"][0]["page"])
        self.assertEqual(
            "10.1007/s11664-018-6220-y",
            material["evidence_refs"][0]["doi"],
        )
        span = material["span"]
        self.assertEqual(
            "UiO-66(Hf5Zr1)-BDC",
            record["evidence_text"][span["start"] : span["end"]],
        )
        coverage = {
            item["field"]: item["status"]
            for item in measurement["condition_coverage"]
        }
        self.assertEqual("reported", coverage["material_identity"])
        self.assertEqual("REVIEW", measurement["review_status"])
        self.assertEqual(
            ["source_relation_unspecified"],
            measurement["review_status_reasons"],
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

    def test_cof_record_binds_post_value_material_without_guessing_provenance(self):
        try:
            from mobility_miner.sources import parse_pdf_path
        except ImportError as error:
            raise unittest.SkipTest("mobility source dependencies unavailable: {}".format(error))

        path = DATA_ROOT / "COF/10.1038_s41467-026-77017-x.pdf"
        records = [
            record
            for record in parse_pdf_path(path, pages=4)
            if record["source"].get("page") == 4
        ]
        matches = [
            (record, measurement)
            for record in records
            for measurement in record.get("fields", {}).get("mobilities", [])
            if measurement.get("value") == 200.0
        ]

        self.assertEqual(1, len(matches))
        record, measurement = matches[0]
        self.assertEqual("unspecified", measurement["source_relation"])
        self.assertNotIn("source_relation_evidence", measurement)
        self.assertEqual([0], measurement["material_refs"])
        self.assertEqual("PI-DY2DP", record["fields"]["materials"][0]["material"])
        self.assertEqual(
            "post_value_for_phrase",
            record["fields"]["materials"][0]["binding_basis"],
        )
        material = next(
            condition
            for condition in measurement["condition_records"]
            if condition["field"] == "material_identity"
        )
        self.assertEqual("PI-DY2DP", material["value"])
        self.assertEqual(4, material["evidence_refs"][0]["page"])
        self.assertEqual(
            "10.1038/s41467-026-77017-x",
            material["evidence_refs"][0]["doi"],
        )
        span = material["span"]
        self.assertEqual(
            "PI-DY2DP",
            record["evidence_text"][span["start"] : span["end"]],
        )
        coverage = {
            item["field"]: item["status"]
            for item in measurement["condition_coverage"]
        }
        self.assertEqual("reported", coverage["material_identity"])

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

    def test_perovskite_records_carry_page_paragraph_doi_and_figure_locator(self):
        try:
            from mobility_miner.sources import parse_pdf_path
        except ImportError as error:
            raise unittest.SkipTest("mobility source dependencies unavailable: {}".format(error))

        path = DATA_ROOT / "PVSK/10.1002_adfm.201902656.pdf"
        records = [record for record in parse_pdf_path(path, pages=7) if record["source"].get("page") == 7]
        matching = [
            measurement
            for record in records
            for measurement in record.get("fields", {}).get("mobilities", [])
            if measurement.get("value_range") == [13.0, 15.0]
        ]

        self.assertTrue(matching)
        measurement = matching[0]
        evidence_ref = measurement["evidence_refs"][0]
        self.assertEqual(7, evidence_ref["page"])
        self.assertIsInstance(evidence_ref["paragraph_index"], int)
        self.assertEqual("10.1002/adfm.201902656", evidence_ref["doi"])
        self.assertEqual("filename_inference", evidence_ref["doi_source"])
        matching_records = [
            record
            for record in records
            if measurement in record.get("fields", {}).get("mobilities", [])
        ]
        self.assertEqual(1, len(matching_records))
        block_locators = matching_records[0]["fields"]["document_locators"]
        self.assertTrue(any(item["raw_text"] == "Figure 3C" for item in block_locators))
        self.assertNotIn("document_locators", measurement)
        self.assertIn("document_locator_unaligned", measurement["review_flags"])
        self.assertNotEqual("prior_work", measurement["source_relation"])
        self.assertFalse(
            any(
                condition["field"] == "sample_form"
                for condition in measurement.get("condition_records", [])
            )
        )
        sample_coverage = {
            item["field"]: item["status"]
            for item in measurement["condition_coverage"]
        }
        self.assertEqual("not_aligned", sample_coverage["sample_form"])
        self.assertIn("sample_form_not_aligned", measurement["review_flags"])
        sample_candidates = [
            condition
            for condition in matching_records[0]["fields"]["condition_candidates"]
            if condition["field"] == "sample_form"
        ]
        self.assertEqual(1, len(sample_candidates))
        sample_candidate = sample_candidates[0]
        self.assertEqual("film", sample_candidate["value"])
        self.assertEqual("films", sample_candidate["raw_text"])
        self.assertEqual("document", sample_candidate["binding_scope"])
        self.assertEqual(["not_bound_to_measurement"], sample_candidate["review_flags"])
        self.assertEqual(7, sample_candidate["evidence_refs"][0]["page"])
        self.assertEqual(
            "10.1002/adfm.201902656",
            sample_candidate["evidence_refs"][0]["doi"],
        )

        current_measurements = [
            candidate
            for record in records
            for candidate in record.get("fields", {}).get("mobilities", [])
            if candidate.get("value") == 13.0 and candidate.get("uncertainty") == 2.0
        ]
        self.assertEqual(1, len(current_measurements))
        current_measurement = current_measurements[0]
        self.assertEqual("current_work", current_measurement["source_relation"])
        self.assertEqual(
            ["current_work"],
            [
                item["cue_type"]
                for item in current_measurement["source_relation_evidence"]
            ],
        )
        self.assertNotIn("material_refs", current_measurement)
        self.assertFalse(
            any(
                condition["field"] == "material_identity"
                for condition in current_measurement.get("condition_records", [])
            )
        )
        coverage = {
            item["field"]: item["status"]
            for item in current_measurement["condition_coverage"]
        }
        self.assertEqual("not_reported", coverage["material_identity"])
        self.assertEqual("not_reported", coverage["sample_form"])

    def test_osm_device_conditions_bind_locally_and_wrong_panel_bias_is_blocked(self):
        try:
            from mobility_miner.sources import parse_pdf_path
        except ImportError as error:
            raise unittest.SkipTest("mobility source dependencies unavailable: {}".format(error))

        path = DATA_ROOT / "OSM/10.1038_ncomms1451.pdf"
        records = [record for record in parse_pdf_path(path, pages=5) if record["source"].get("page") == 5]
        measurements = [
            measurement
            for record in records
            for measurement in record.get("fields", {}).get("mobilities", [])
        ]
        device_measurements = [
            measurement
            for measurement in measurements
            if any(
                condition["field"] == "device_type"
                for condition in measurement.get("condition_records", [])
            )
        ]
        saturation = next(item for item in device_measurements if item.get("value") == 12.3)
        linear = next(item for item in device_measurements if item.get("value") == 16.0)

        for measurement in (saturation, linear):
            device = next(
                condition
                for condition in measurement["condition_records"]
                if condition["field"] == "device_type"
            )
            self.assertEqual("single-crystal field-effect transistor", device["value"])
            self.assertEqual(5, device["evidence_refs"][0]["page"])
            self.assertEqual("10.1038/ncomms1451", device["evidence_refs"][0]["doi"])
            conditions = {
                condition["field"]: condition
                for condition in measurement["condition_records"]
            }
            self.assertEqual(
                "bottom-contact, bottom-gate geometry",
                conditions["device_geometry"]["raw_text"],
            )
            self.assertEqual("Au bottom contacts", conditions["electrode"]["raw_text"])
            self.assertEqual(
                "manually laminated",
                conditions["fabrication_method"]["raw_text"],
            )
            coverage = {
                item["field"]: item["status"]
                for item in measurement["condition_coverage"]
            }
            for field in (
                "device_fabrication",
                "device_geometry",
                "electrode",
                "fabrication_method",
            ):
                self.assertEqual("reported", coverage[field])
            self.assertEqual("not_reported", coverage["synthesis_processing"])
            for field in ("device_geometry", "electrode", "fabrication_method"):
                linked_condition = conditions[field]
                self.assertEqual("normalized_page_text", linked_condition["span_scope"])
                self.assertEqual(
                    "same_device_type",
                    linked_condition["relation_path"][0]["relation"],
                )
                evidence_ref = linked_condition["evidence_refs"][0]
                self.assertEqual(5, evidence_ref["page"])
                self.assertEqual("10.1038/ncomms1451", evidence_ref["doi"])

        linear_condition_fields = {
            condition["field"] for condition in linear.get("condition_records", [])
        }
        linear_coverage = {
            item["field"]: item["status"] for item in linear["condition_coverage"]
        }
        self.assertNotIn("drain_source_voltage", linear_condition_fields)
        self.assertEqual("not_aligned", linear_coverage["drain_source_voltage"])
        self.assertIn("drain_source_voltage_not_aligned", linear["review_flags"])


if __name__ == "__main__":
    unittest.main()

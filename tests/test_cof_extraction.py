from framework_miner.cof import (
    heuristic_cof_fields,
    heuristic_cof_monomers,
    heuristic_cof_names,
    is_cof_candidate_text,
)
from framework_miner.legacy_digimof import merge_items, parse_html_text


SUZUKI_COF_TEXT = (
    "C-C bonded two-dimensional conjugated covalent organic framework films "
    "2DCCOF1 and 2DCCOF2 were synthesized from aryl diboronic ester and "
    "porphyrin monomer by Suzuki polymerization at a "
    "water/toluene interface using Pd(PPh3)4 and K2CO3 under argon at 2 °C "
    "for one month."
)


def test_cof_candidate_text():
    assert is_cof_candidate_text("A covalent organic framework was synthesized.")
    assert is_cof_candidate_text("Suzuki polymerization produced a crystalline film.")
    assert not is_cof_candidate_text("This paragraph discusses ordinary organic molecules.")


def test_heuristic_cof_names():
    assert heuristic_cof_names(SUZUKI_COF_TEXT) == ["2DCCOF1", "2DCCOF2"]


def test_heuristic_cof_fields_suzuki_film():
    fields = heuristic_cof_fields(SUZUKI_COF_TEXT)

    assert fields is not None
    assert fields["names"] == ["2DCCOF1", "2DCCOF2"]
    assert {"route": "Suzuki polymerization"} in fields["polymerization_routes"]
    assert fields["linkages"] == [{"linkage": "C-C bonded"}]
    assert {"monomer": "aryl diboronic ester", "role": "from"} in fields["monomers"]
    assert {"monomer": "porphyrin monomer", "role": "from"} in fields["monomers"]
    assert {"catalyst": "Pd(PPh3)4"} in fields["catalysts"]
    assert {"base": "K2CO3"} in fields["bases"]
    assert {"interface": "water/toluene interface"} in fields["interfaces"]
    assert {"solvent": "toluene"} in fields["solvents"]
    assert {"solvent": "water"} in fields["solvents"]
    assert fields["temperature"] == ["2 °C"]
    assert fields["time"] == ["one month"]


def test_heuristic_cof_monomers_from_and_between_patterns():
    from_text = "COF-1 was synthesized from 1,3,5-triformylbenzene and p-phenylenediamine."
    between_text = "A COF was formed between TFP and TAPB under solvothermal conditions."

    assert heuristic_cof_monomers(from_text) == [
        {"monomer": "1,3,5-triformylbenzene", "role": "from"},
        {"monomer": "p-phenylenediamine", "role": "from"},
    ]
    assert heuristic_cof_monomers(between_text) == [
        {"monomer": "TFP", "role": "between"},
        {"monomer": "TAPB", "role": "between"},
    ]


def test_parse_html_text_cof_framework():
    html = (
        "<html><body><p>Official site text that should be ignored.</p>"
        "<p>{}</p></body></html>".format(SUZUKI_COF_TEXT)
    ).encode("utf-8")

    records = list(merge_items(parse_html_text(html, "memory://cof", framework="cof")))

    assert len(records) == 1
    assert records[0]["framework_type"] == "COF"
    assert records[0]["fields"]["names"] == ["2DCCOF1", "2DCCOF2"]
    assert records[0]["extraction_method"] == "cof_paragraph_heuristic"


def test_heuristic_cof_fields_imine_route():
    text = (
        "An imine-linked PyTTA-TPA-COF was obtained by Schiff base "
        "polycondensation of PyTTA with TPA in mesitylene and 1,4-dioxane "
        "at 120 °C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["PyTTA-TPA-COF"]
    assert {"linkage": "imine-linked"} in fields["linkages"]
    assert {"route": "Schiff base polycondensation"} in fields["polymerization_routes"]
    assert {"monomer": "PyTTA", "role": "polycondensation"} in fields["monomers"]
    assert {"monomer": "TPA", "role": "polycondensation"} in fields["monomers"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "1,4-dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["120 °C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_hydrazone_room_temperature():
    text = (
        "A hydrazone-linked TFPPy-DETHz-COF was synthesized by hydrazone "
        "formation from 1,3,6,8-tetrakis(4-formylphenyl)pyrene and "
        "2,5-diethoxyterephthalohydrazide in mesitylene/dioxane with "
        "acetic acid at room temperature for three days."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TFPPy-DETHz-COF"]
    assert {"route": "hydrazone formation"} in fields["polymerization_routes"]
    assert {"linkage": "hydrazone-linked"} in fields["linkages"]
    assert {"monomer": "1,3,6,8-tetrakis(4-formylphenyl)pyrene", "role": "from"} in fields["monomers"]
    assert {"monomer": "2,5-diethoxyterephthalohydrazide", "role": "from"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["room temperature"]
    assert fields["time"] == ["three days"]


def test_heuristic_cof_fields_boronate_ester_route():
    text = (
        "Boronate ester COF-5 was synthesized from 1,4-benzenediboronic acid "
        "and 2,3,6,7,10,11-hexahydroxytriphenylene through boronate ester "
        "condensation in mesitylene and 1,4-dioxane at 85 °C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-5"]
    assert {"route": "boronate ester condensation"} in fields["polymerization_routes"]
    assert {"linkage": "boronate ester"} in fields["linkages"]
    assert {"monomer": "1,4-benzenediboronic acid", "role": "from"} in fields["monomers"]
    assert {"monomer": "2,3,6,7,10,11-hexahydroxytriphenylene", "role": "from"} in fields["monomers"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "1,4-dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["85 °C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_knoevenagel_olefin_route():
    text = (
        "An olefin-linked COF-V was prepared by Knoevenagel condensation of "
        "1,3,5-triformylbenzene with 2,4,6-trimethyl-1,3,5-triazine using "
        "piperidine in dioxane at 120 °C for 3 days."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-V"]
    assert {"route": "Knoevenagel condensation"} in fields["polymerization_routes"]
    assert {"linkage": "olefin-linked"} in fields["linkages"]
    assert {"monomer": "1,3,5-triformylbenzene", "role": "condensation"} in fields["monomers"]
    assert {"monomer": "2,4,6-trimethyl-1,3,5-triazine", "role": "condensation"} in fields["monomers"]
    assert {"base": "piperidine"} in fields["bases"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["120 °C"]
    assert fields["time"] == ["3 days"]


def test_heuristic_cof_fields_beta_ketoenamine_overnight():
    text = (
        "A beta-ketoenamine-linked TpPa-1 COF was synthesized by "
        "Schiff-base condensation of 1,3,5-triformylphloroglucinol with "
        "p-phenylenediamine in mesitylene/dioxane with 6 M acetic acid "
        "at 120 °C for overnight."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TpPa-1 COF"]
    assert {"route": "Schiff-base condensation"} in fields["polymerization_routes"]
    assert {"linkage": "beta-ketoenamine-linked"} in fields["linkages"]
    assert {"monomer": "1,3,5-triformylphloroglucinol", "role": "condensation"} in fields["monomers"]
    assert {"monomer": "p-phenylenediamine", "role": "condensation"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["120 °C"]
    assert fields["time"] == ["overnight"]

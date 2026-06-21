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
    assert {"atmosphere": "argon"} in fields["atmospheres"]
    assert {"interface": "water/toluene interface"} in fields["interfaces"]
    assert {"solvent": "toluene"} in fields["solvents"]
    assert {"solvent": "water"} in fields["solvents"]
    assert fields["temperature"] == ["2 °C"]
    assert fields["time"] == ["one month"]


def test_heuristic_cof_monomers_from_and_between_patterns():
    from_text = "COF-1 was synthesized from 1,3,5-triformylbenzene and p-phenylenediamine."
    between_text = "A COF was formed between TFP and TAPB under solvothermal conditions."
    reaction_text = (
        "TpPa-1 COF was obtained by the reaction of 1,3,5-triformylphloroglucinol "
        "with p-phenylenediamine in mesitylene/dioxane."
    )
    polymerization_text = (
        "A vinylene-linked COF was formed by polymerization of 2,4,6-trimethyl-1,3,5-triazine "
        "with terephthaldehyde under ionothermal conditions."
    )

    assert heuristic_cof_monomers(from_text) == [
        {"monomer": "1,3,5-triformylbenzene", "role": "from"},
        {"monomer": "p-phenylenediamine", "role": "from"},
    ]
    assert heuristic_cof_monomers(between_text) == [
        {"monomer": "TFP", "role": "between"},
        {"monomer": "TAPB", "role": "between"},
    ]
    assert heuristic_cof_monomers(reaction_text) == [
        {"monomer": "1,3,5-triformylphloroglucinol", "role": "reaction"},
        {"monomer": "p-phenylenediamine", "role": "reaction"},
    ]
    assert heuristic_cof_monomers(polymerization_text) == [
        {"monomer": "2,4,6-trimethyl-1,3,5-triazine", "role": "polymerization"},
        {"monomer": "terephthaldehyde", "role": "polymerization"},
    ]


def test_heuristic_cof_monomers_coupling_patterns():
    text = (
        "A C-C bonded COF was formed by Suzuki coupling of "
        "1,3,6,8-tetrabromopyrene with benzene-1,4-diboronic acid in toluene/water."
    )

    assert heuristic_cof_monomers(text) == [
        {"monomer": "1,3,6,8-tetrabromopyrene", "role": "coupling"},
        {"monomer": "benzene-1,4-diboronic acid", "role": "coupling"},
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


def test_heuristic_cof_fields_real_carrier_gas_flow():
    text = (
        "PyTTA-TPA, PyTTA-BPyDCA, and PyTTA-BPDA COF films were grown on various "
        "substrates by vapor-induced conversion in a CVD system. The tube furnace "
        "is externally connected with a bubbler to hold a 20 ml deionized aqueous "
        "solution of acetic acid (Vacid/Vwater = 9:1) and a hydrogen and argon flow "
        "of 10 sccm and 10 sccm is used as carrier gas."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert {"route": "vapor induced conversion"} in fields["polymerization_routes"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "water"} in fields["solvents"]
    assert {"atmosphere": "hydrogen"} in fields["atmospheres"]
    assert {"atmosphere": "argon"} in fields["atmospheres"]


def test_heuristic_cof_fields_real_surface_substrate():
    text = (
        "Here, we present syntheses of two-dimensional and liner COFs substructures "
        "linked with 1,4-disilabenzene (C4Si2) by co-depositing silicon atoms and "
        "bromo-substituted poly aromatic hydrocarbons on Au(111)."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert {"monomer": "silicon atoms", "role": "codeposition"} in fields["monomers"]
    assert {
        "monomer": "bromo-substituted poly aromatic hydrocarbons",
        "role": "codeposition",
    } in fields["monomers"]
    assert fields["substrates"] == [{"substrate": "Au(111)"}]


def test_heuristic_cof_fields_real_azomethine_surface_growth():
    text = (
        "Two dimensional pi conjugated metal porphyrin covalent organic frameworks "
        "were produced in aqueous solution on an iodine-modified Au(111) surface by "
        "on site azomethine coupling of Fe(III) 5,10,15,20 tetrakis(4 aminophenyl)"
        "porphyrin (FeTAPP) with terephthal dicarboxaldehyde and investigated in "
        "detail using in-situ scanning tunneling microscopy."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert {"route": "azomethine coupling"} in fields["polymerization_routes"]
    assert {"monomer": "Fe(III) 5,10,15,20 tetrakis(4 aminophenyl)porphyrin (FeTAPP)", "role": "coupling"} in fields["monomers"]
    assert {"monomer": "terephthal dicarboxaldehyde", "role": "coupling"} in fields["monomers"]
    assert {"monomer": "investigated", "role": "coupling"} not in fields["monomers"]
    assert fields["solvents"] == [{"solvent": "water"}]
    assert fields["substrates"] == [{"substrate": "Au(111)"}]


def test_heuristic_cof_fields_real_tfpt_experimental_workup_precision():
    text = (
        "TFPT-COF To a Biotage 5 mL microwave vial 17.7 mg (0.044 mmol, 2.0 eq.) "
        "of TFPT (1) and a stir bar was added. Then 18.6 mg (0.066 mmol, 3.0 eq.) "
        "of 2,5-diethyoxy-terephthalohydrazide was added and the vial was temporally "
        "sealed with a rubber septum. Subsequently, the vial was flushed three times "
        "in argon/vacuum cycles. To the mixture 0.66 mL of mesitylene and 0.33 mL "
        "of 1,4-dioxane were added and again degassed three times in argon/vacuum "
        "cycles. In one shot 100 µL aqueous 6M acetic acid was added, the vial was "
        "sealed and heated in a stirred oil bath with 120 °C (preheated) on a "
        "heating stirrer for 72 h. After slow cooling to room temperature the vial "
        "was opened and the whole mixture was centrifuged (3 x 15 min, 20000 rpm) "
        "while being washed with DMF (1 x 7 mL) and THF (2 x 7 mL). The resulting "
        "yellow precipitate was transferred to a storage vial with DCM, dried at "
        "room temperature, then in vacuum and characterized by powder X-ray "
        "diffraction."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TFPT-COF"]
    assert {"monomer": "TFPT", "role": "addition"} in fields["monomers"]
    assert {"monomer": "2,5-diethyoxy-terephthalohydrazide", "role": "addition"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert fields["solvents"] == [{"solvent": "1,4-dioxane"}, {"solvent": "mesitylene"}]
    assert fields["temperature"] == ["120 °C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_real_ullmann_surface_route_without_2d_time():
    text = (
        "Relative to conventional wet-chemical synthesis techniques, on-surface "
        "synthesis of organic networks in ultrahigh vacuum has few control "
        "parameters. The molecular deposition rate and substrate temperature are "
        "typically the only synthesis variables to be adjusted dynamically. Here "
        "we demonstrate that reducing conditions in the vacuum environment can be "
        "created and controlled without dedicated sources -- relying only on "
        "backfilled hydrogen gas and ion gauge filaments -- and can dramatically "
        "influence the Ullmann-like on-surface reaction used for synthesizing "
        "two-dimensional covalent organic frameworks (2D COFs). Using tribromo "
        "dimethylmethylene-bridged triphenylamine ((Br3)DTPA) as monomer "
        "precursors, we find that atomic hydrogen blocks aryl-aryl bond formation."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["polymerization_routes"] == [{"route": "Ullmann coupling"}]
    assert "time" not in fields


def test_heuristic_cof_fields_real_ullmann_surface_using_monomer_precursor():
    text = (
        "Relative to conventional wet-chemical synthesis techniques, on-surface "
        "synthesis of organic networks in ultrahigh vacuum has few control "
        "parameters. The molecular deposition rate and substrate temperature are "
        "typically the only synthesis variables to be adjusted dynamically. Here "
        "we demonstrate that reducing conditions in the vacuum environment can be "
        "created and controlled without dedicated sources -- relying only on "
        "backfilled hydrogen gas and ion gauge filaments -- and can dramatically "
        "influence the Ullmann-like on-surface reaction used for synthesizing "
        "two-dimensional covalent organic frameworks (2D COFs). Using tribromo "
        "dimethylmethylene-bridged triphenylamine ((Br3)DTPA) as monomer "
        "precursors, we find that atomic hydrogen blocks aryl-aryl bond formation."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["polymerization_routes"] == [{"route": "Ullmann coupling"}]
    assert fields["monomers"] == [
        {
            "monomer": "tribromo dimethylmethylene-bridged triphenylamine ((Br3)DTPA)",
            "role": "using",
        }
    ]
    assert "time" not in fields


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


def test_heuristic_cof_fields_reaction_wording():
    text = (
        "A beta-ketoenamine-linked TpPa-1 COF was obtained by the reaction "
        "of 1,3,5-triformylphloroglucinol with p-phenylenediamine in "
        "mesitylene/dioxane with acetic acid at 120 °C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TpPa-1 COF"]
    assert {"monomer": "1,3,5-triformylphloroglucinol", "role": "reaction"} in fields["monomers"]
    assert {"monomer": "p-phenylenediamine", "role": "reaction"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["120 °C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_catalyst_abbreviation_normalization():
    text = (
        "An imine-linked COF-380 was synthesized from TAPB and terephthaldehyde "
        "in mesitylene/dioxane with 6 M AcOH and TFA at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-380"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"catalyst": "trifluoroacetic acid"} in fields["catalysts"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_base_abbreviation_normalization():
    text = (
        "A vinylene-linked COF-381 was prepared by Knoevenagel condensation of "
        "TFPT with PDAN using Et3N and Hunig's base in acetonitrile at 70 \u00b0C for 24 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-381"]
    assert {"route": "Knoevenagel condensation"} in fields["polymerization_routes"]
    assert {"linkage": "vinylene-linked"} in fields["linkages"]
    assert {"monomer": "TFPT", "role": "condensation"} in fields["monomers"]
    assert {"monomer": "PDAN", "role": "condensation"} in fields["monomers"]
    assert {"base": "triethylamine"} in fields["bases"]
    assert {"base": "DIPEA"} in fields["bases"]
    assert {"solvent": "acetonitrile"} in fields["solvents"]
    assert fields["temperature"] == ["70 \u00b0C"]
    assert fields["time"] == ["24 h"]


def test_heuristic_cof_fields_solvent_abbreviation_normalization():
    text = (
        "An imine-linked COF-382 was synthesized from TAPB and terephthaldehyde "
        "in MeCN/o-DCB with n-BuOH and 6 M AcOH at 85 \u00b0C for 48 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-382"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "acetonitrile"} in fields["solvents"]
    assert {"solvent": "1,2-dichlorobenzene"} in fields["solvents"]
    assert {"solvent": "n-butanol"} in fields["solvents"]
    assert fields["temperature"] == ["85 \u00b0C"]
    assert fields["time"] == ["48 h"]


def test_heuristic_cof_fields_dichloromethane_alias_normalization():
    text = (
        "An imine-linked COF-383 was synthesized from TAPB and terephthaldehyde "
        "in CH2Cl2/DCM with 6 M AcOH at room temperature for 24 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-383"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert fields["solvents"] == [{"solvent": "dichloromethane"}]
    assert fields["temperature"] == ["room temperature"]
    assert fields["time"] == ["24 h"]


def test_heuristic_cof_fields_extended_solvent_alias_normalization():
    text = (
        "An imine-linked COF-384 was synthesized from TAPB and terephthaldehyde "
        "in MeOH/EtOH/tetrahydrofuran with N,N-dimethylformamide and "
        "N,N-dimethylacetamide at 90 \u00b0C for 24 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-384"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"solvent": "methanol"} in fields["solvents"]
    assert {"solvent": "ethanol"} in fields["solvents"]
    assert {"solvent": "THF"} in fields["solvents"]
    assert {"solvent": "DMF"} in fields["solvents"]
    assert {"solvent": "DMAc"} in fields["solvents"]
    assert fields["temperature"] == ["90 \u00b0C"]
    assert fields["time"] == ["24 h"]


def test_heuristic_cof_fields_condensation_of_a_and_b_wording():
    text = (
        "An imine-linked COF-300 was obtained by Schiff-base condensation "
        "of 1,3,5-triformylbenzene and p-phenylenediamine in "
        "mesitylene/dioxane at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-300"]
    assert {"route": "Schiff-base condensation"} in fields["polymerization_routes"]
    assert {"linkage": "imine-linked"} in fields["linkages"]
    assert {"monomer": "1,3,5-triformylbenzene", "role": "condensation"} in fields["monomers"]
    assert {"monomer": "p-phenylenediamine", "role": "condensation"} in fields["monomers"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_vapor_induced_conversion_aliases():
    text = (
        "A crystalline COF-VIC film was prepared on indium tin oxide glass from TAPB and "
        "terephthaldehyde by vapor-induced conversion (VIC) in mesitylene/dioxane with "
        "6 M AcOH at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-VIC"]
    assert {"route": "vapor induced conversion"} in fields["polymerization_routes"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert {"substrate": "ITO glass"} in fields["substrates"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_interface_alias_normalization():
    text = (
        "A crystalline COF-390 film was synthesized from TAPB and terephthaldehyde at the "
        "air/water interface in mesitylene/dioxane with 6 M AcOH at room temperature for 24 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-390"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"interface": "air-water interface"} in fields["interfaces"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert fields["temperature"] == ["room temperature"]
    assert fields["time"] == ["24 h"]


def test_heuristic_cof_fields_real_article_compact_celsius():
    text = (
        "TFPT-COF was synthesized by the acetic acid catalysed reversible condensation "
        "of the building blocks in dioxane/mesitylene (1:2 v/v) at 120\u00b0C in a sealed "
        "pressure vial under argon atmosphere for 72 hours."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TFPT-COF"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "dioxane"} in fields["solvents"]
    assert {"solvent": "mesitylene"} in fields["solvents"]
    assert {"atmosphere": "argon"} in fields["atmospheres"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 hours"]


def test_heuristic_cof_fields_real_article_hyphenated_growth_duration():
    text = (
        "PyTTA-TPA, PyTTA-BPyDCA, and PyTTA-BPDA COF films were grown on various "
        "substrates by vapor-induced conversion in a CVD system. The tube furnace is "
        "externally connected with a bubbler to hold a 20 ml deionized aqueous solution "
        "of acetic acid (Vacid/Vwater = 9:1). The center heating zone was heated to "
        "140 \u00b0C. After a 7-day growth, the central heating zone was heated to 180 "
        "\u00b0C for 1 h. The furnace was then cooled to room temperature to obtain COF films."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert {"route": "vapor induced conversion"} in fields["polymerization_routes"]
    assert {"catalyst": "acetic acid"} in fields["catalysts"]
    assert {"solvent": "water"} in fields["solvents"]
    assert fields["temperature"] == ["140 \u00b0C", "180 \u00b0C", "room temperature"]
    assert fields["time"] == ["7-day", "1 h"]


def test_heuristic_cof_fields_real_article_ignores_auxiliary_powder_temperatures():
    text = (
        "PyTTA-TPA, PyTTA-BPyDCA, and PyTTA-BPDA COF films were grown on various "
        "substrates by vapor-induced conversion in a CVD system. The center heating zone "
        "was heated to 140 \u00b0C. Note that the temperature of the TPA (or BPyDCA, BPDA) "
        "powders was controlled at \u223c80 \u00b0C (105 \u00b0C for BPyDCA, 110 \u00b0C for "
        "BPDA) when the center heating zone reaches 140 \u00b0C. After a 7-day growth, the "
        "central heating zone was heated to 180 \u00b0C for 1 h. The furnace was then cooled "
        "to room temperature to obtain COF films."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert {"route": "vapor induced conversion"} in fields["polymerization_routes"]
    assert fields["temperature"] == ["140 \u00b0C", "180 \u00b0C", "room temperature"]
    assert fields["time"] == ["7-day", "1 h"]


def test_heuristic_cof_fields_real_article_ignores_characterization_kelvin():
    text = (
        "We synthesized a pure organic non-metal crystalline covalent organic framework "
        "TAPA-BTD-COF by bottom-up Schiff base chemical reaction. And this imine-based COF "
        "is stable in aerobic condition and room-temperature. We discovered that this "
        "TAPA-BTD-COF exhibited strong magneticity in 300 K generating magnetic hysteresis "
        "loop in M-H characterization."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TAPA-BTD-COF"]
    assert fields["polymerization_routes"] == [{"route": "Schiff base chemical reaction"}]
    assert fields["linkages"] == [{"linkage": "imine"}]
    assert fields["temperature"] == ["room temperature"]


def test_heuristic_cof_fields_real_article_ignores_generic_new_cof_name():
    text = (
        "Covalent organic frameworks (COFs) have recently emerged as a new generation of "
        "porous polymers combining molecular functionality with the robustness and structural "
        "definition of crystalline solids. Drawing on the recent development of tailor-made "
        "semiconducting COFs, we here report on a new COF capable of visible-light driven "
        "hydrogen generation. The COF is based on hydrazone-linked functionalized triazine "
        "and phenyl building blocks and adopts a layered structure with a honeycomb-type "
        "lattice featuring mesopores of 3.8 nm and the highest surface area among all "
        "hydrazone-based COFs reported to date."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert "names" not in fields
    assert {"linkage": "hydrazone-linked"} in fields["linkages"]


def test_heuristic_cof_fields_real_article_descriptor_before_family_name():
    text = (
        "Using a Wurster-type tetratopic amine (W-NH2) and a series of anthracene-based "
        "dialdehydes bearing H, Cl, Br, or I at the 2-position, a family of imine-linked "
        "COFs, W-A-X (X = H, Cl, Br, I), was synthesized, all displaying well-ordered porous "
        "structures."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["W-A-X (X = H, Cl, Br, I)"]
    assert fields["linkages"] == [{"linkage": "imine-linked"}]


def test_heuristic_cof_fields_real_article_using_monomers_before_family_name():
    text = (
        "Using a Wurster-type tetratopic amine (W-NH2) and a series of anthracene-based "
        "dialdehydes bearing H, Cl, Br, or I at the 2-position, a family of imine-linked "
        "COFs, W-A-X (X = H, Cl, Br, I), was synthesized, all displaying well-ordered porous "
        "structures."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["W-A-X (X = H, Cl, Br, I)"]
    assert fields["linkages"] == [{"linkage": "imine-linked"}]
    assert {"monomer": "Wurster-type tetratopic amine (W-NH2)", "role": "using"} in fields["monomers"]
    assert {
        "monomer": "series of anthracene-based dialdehydes bearing H, Cl, Br, or I at the 2-position",
        "role": "using",
    } in fields["monomers"]


def test_heuristic_cof_temperature_variants_are_normalized():
    text = "TpPa-1 COF was synthesized at 85 \u2103 and then heated to 120 \u63b3C for 72 h."
    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["temperature"] == ["85 \u00b0C", "120 \u00b0C"]


def test_heuristic_cof_fields_suzuki_coupling_wording():
    text = (
        "A C-C bonded COF-LZU1 was formed by Suzuki coupling of "
        "1,3,6,8-tetrabromopyrene with benzene-1,4-diboronic acid "
        "using Pd(PPh3)4 and K2CO3 at the water/toluene interface at 90 \u00b0C for 48 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-LZU1"]
    assert {"route": "Suzuki coupling"} in fields["polymerization_routes"]
    assert {"linkage": "C-C bonded"} in fields["linkages"]
    assert {"monomer": "1,3,6,8-tetrabromopyrene", "role": "coupling"} in fields["monomers"]
    assert {"monomer": "benzene-1,4-diboronic acid", "role": "coupling"} in fields["monomers"]
    assert {"catalyst": "Pd(PPh3)4"} in fields["catalysts"]
    assert {"base": "K2CO3"} in fields["bases"]
    assert {"interface": "water/toluene interface"} in fields["interfaces"]
    assert {"solvent": "toluene"} in fields["solvents"]
    assert {"solvent": "water"} in fields["solvents"]
    assert fields["temperature"] == ["90 \u00b0C"]
    assert fields["time"] == ["48 h"]


def test_heuristic_cof_fields_atmosphere_wording():
    text = (
        "An imine-linked COF-320 was prepared by Schiff base polycondensation "
        "of TAPB with terephthaldehyde in mesitylene/dioxane under nitrogen "
        "at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-320"]
    assert {"route": "Schiff base polycondensation"} in fields["polymerization_routes"]
    assert {"monomer": "TAPB", "role": "polycondensation"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "polycondensation"} in fields["monomers"]
    assert {"atmosphere": "nitrogen"} in fields["atmospheres"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_atmosphere_of_wording():
    text = (
        "An imine-linked COF-333 was synthesized from TAPB and terephthaldehyde "
        "in mesitylene/dioxane at 120 \u00b0C for 72 h under an atmosphere of argon."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-333"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"atmosphere": "argon"} in fields["atmospheres"]


def test_heuristic_cof_fields_atmosphere_shorthand_wording():
    text = (
        "An imine-linked COF-345 was synthesized from TAPB and terephthaldehyde "
        "in mesitylene/dioxane under N2 atmosphere at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-345"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"atmosphere": "nitrogen"} in fields["atmospheres"]


def test_heuristic_cof_fields_inert_atmosphere_wording():
    text = (
        "A C-C bonded COF-LZU2 was formed by Suzuki coupling of "
        "1,3,6,8-tetrabromopyrene with benzene-1,4-diboronic acid "
        "using Pd(PPh3)4 and K2CO3 under inert atmosphere at 90 \u00b0C for 48 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-LZU2"]
    assert {"atmosphere": "inert atmosphere"} in fields["atmospheres"]


def test_heuristic_cof_fields_atmosphere_flow_wording():
    text = (
        "An imine-linked COF-360 was synthesized from TAPB and terephthaldehyde "
        "in mesitylene/dioxane under a flow of nitrogen at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-360"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert {"atmosphere": "nitrogen"} in fields["atmospheres"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_atmosphere_flow_shorthand_wording():
    text = (
        "An imine-linked COF-361 was synthesized from TAPB and terephthaldehyde "
        "in mesitylene/dioxane under Ar stream at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-361"]
    assert {"atmosphere": "argon"} in fields["atmospheres"]


def test_heuristic_cof_fields_substrate_wording():
    text = (
        "A vinylene-linked COF-TFPT was prepared on indium tin oxide glass "
        "by Knoevenagel condensation of TFPT with PDAN in acetonitrile "
        "at 70 \u00b0C for 24 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-TFPT"]
    assert {"route": "Knoevenagel condensation"} in fields["polymerization_routes"]
    assert {"monomer": "TFPT", "role": "condensation"} in fields["monomers"]
    assert {"monomer": "PDAN", "role": "condensation"} in fields["monomers"]
    assert {"substrate": "ITO glass"} in fields["substrates"]
    assert {"solvent": "acetonitrile"} in fields["solvents"]
    assert fields["temperature"] == ["70 \u00b0C"]
    assert fields["time"] == ["24 h"]


def test_heuristic_cof_fields_substrate_shorthand_wording():
    text = (
        "An imine-linked COF-370 was grown on silicon wafer from TAPB and "
        "terephthaldehyde in mesitylene/dioxane at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-370"]
    assert {"substrate": "silicon wafer"} in fields["substrates"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]


def test_heuristic_cof_fields_substrate_acronym_and_onto_wording():
    text = (
        "A vinylene-linked COF-FTO was deposited onto fluorine-doped tin oxide "
        "(FTO) glass by Knoevenagel condensation of TFPT with PDAN in "
        "acetonitrile at 70 \u00b0C for 24 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-FTO"]
    assert {"route": "Knoevenagel condensation"} in fields["polymerization_routes"]
    assert {"monomer": "TFPT", "role": "condensation"} in fields["monomers"]
    assert {"monomer": "PDAN", "role": "condensation"} in fields["monomers"]
    assert {"substrate": "FTO glass"} in fields["substrates"]
    assert {"solvent": "acetonitrile"} in fields["solvents"]
    assert fields["temperature"] == ["70 \u00b0C"]
    assert fields["time"] == ["24 h"]


def test_heuristic_cof_fields_substrate_shorthand_alias_wording():
    text = (
        "An imine-linked COF-371 was supported on ITO substrate from TAPB and "
        "terephthaldehyde in mesitylene/dioxane at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-371"]
    assert {"substrate": "ITO glass"} in fields["substrates"]
    assert {"monomer": "TAPB", "role": "from"} in fields["monomers"]
    assert {"monomer": "terephthaldehyde", "role": "from"} in fields["monomers"]
    assert fields["temperature"] == ["120 \u00b0C"]
    assert fields["time"] == ["72 h"]


def test_heuristic_cof_fields_do_not_infer_air_stable_as_atmosphere():
    text = (
        "An imine-linked COF-320 was prepared from an air-stable aldehyde monomer "
        "and TAPB in mesitylene/dioxane at 120 \u00b0C for 72 h."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["COF-320"]
    assert "atmospheres" not in fields


def test_heuristic_cof_fields_real_article_schiff_base_reaction():
    text = (
        "We synthesized a pure organic non-metal crystalline covalent organic framework "
        "TAPA-BTD-COF by bottom-up Schiff base chemical reaction."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TAPA-BTD-COF"]
    assert {"route": "Schiff base chemical reaction"} in fields["polymerization_routes"]


def test_heuristic_cof_fields_real_article_imine_based_linkage():
    text = (
        "We synthesized a pure organic non-metal crystalline covalent organic framework "
        "TAPA-BTD-COF by bottom-up Schiff base chemical reaction. And this imine-based "
        "COF is stable in aerobic condition and room-temperature."
    )

    fields = heuristic_cof_fields(text)

    assert fields is not None
    assert fields["names"] == ["TAPA-BTD-COF"]
    assert {"route": "Schiff base chemical reaction"} in fields["polymerization_routes"]
    assert {"linkage": "imine"} in fields["linkages"]

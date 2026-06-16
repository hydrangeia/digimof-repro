# Product Notes

这个项目现在按“合成信息抽取产品原型”推进，而不是按“大而全数据库”推进。

## 当前产品判断

优先级：

1. 准确性优先于覆盖率。
2. 合成信息优先于性质/性能信息。
3. 开放全文优先；遇到付费墙直接换文献。
4. 小 benchmark 驱动规则迭代，每次改规则都要证明核心字段没有退化。

## 核心字段

MOF 当前优先字段：

- `names`
- `synthesis_routes`
- `topologies`
- `linker_routes`

COF 当前优先字段：

- `names`
- `polymerization_routes`
- `linkages`
- `monomers`
- `catalysts`
- `bases`
- `solvents`
- `atmospheres`
- `interfaces`
- `substrates`
- `temperature`
- `time`

暂时不优先：

- 大规模抓取。
- 付费文献处理。
- 图表/补充信息复杂解析。
- 性质表格和性能指标。
- 单体名标准化。

## 为什么要 benchmark

规则抽取很容易“多抽一点，同时误抽更多”。因此当前策略是：

1. 先写一个 gold case。
2. 明确期望字段。
3. 再改规则。
4. 跑 `evaluate_framework_miner.py` 和 `pytest`。

当前命令：

```powershell
conda run -n digimof-repro python evaluate_framework_miner.py
conda run -n digimof-repro pytest tests -q -p no:cacheprovider --basetemp .pytest_tmp
```

当前目标结果：

```text
cases: 34/34 passed
field recall: 246/246
61 passed
```

## 下一步建议

短期最值得做：

1. 把已经覆盖的 COF 合成路线换成真实开放文献片段继续校准：
   - Suzuki polymerization
   - Schiff base polycondensation
   - Schiff-base condensation / beta-ketoenamine
   - Knoevenagel condensation
   - boronate ester condensation
   - hydrazone formation
   - reaction of A with B wording
2. 每类 MOF 合成路线各加 1 个 gold case：
   - solvothermal
   - hydrothermal
   - mechanochemical
   - electrochemical
3. 只在 benchmark 暴露出漏抽/误抽时加规则。

中期再考虑：

- monomer normalization。
- DOI/URL source metadata enrichment。
- 人工审阅表导出。
- 简单网页界面。
## 2026-06-12 note

Benchmark coverage now includes a COF `Suzuki coupling of A with B` case so monomer recall is checked for coupling wording, not only for `Suzuki polymerization`.
Benchmark coverage now also includes `Schiff-base condensation of A and B`, and the COF monomer heuristic handles this `of A and B` wording in addition to the earlier `of A with B` form.
COF extraction now emits an `atmospheres` field for straightforward condition wording such as `under argon` and `under nitrogen`, and the Suzuki gold case checks that inert-gas condition explicitly.
COF atmosphere extraction is now condition-scoped instead of raw keyword matching: it keeps forms like `under nitrogen` and `under an atmosphere of argon`, but ignores unrelated wording such as `air-stable` so the field is less noisy.
COF atmosphere extraction now also normalizes shorthand inert-gas wording such as `under N2 atmosphere` to the canonical `nitrogen` field value, so benchmark and JSONL outputs are less fragmented.
COF atmosphere extraction now also captures explicit flow phrasing such as `under a flow of nitrogen` and `under Ar stream`, which appears in synthesis procedures that describe purge conditions instead of `under nitrogen atmosphere`.
COF extraction now also emits a `substrates` field for film-growth wording such as `prepared on indium tin oxide glass` and normalizes long forms like `indium tin oxide glass` to `ITO glass` so support-substrate information is easier to query in JSONL outputs.
COF substrate extraction now also handles `deposited onto fluorine-doped tin oxide (FTO) glass` style wording and normalizes it to `FTO glass`, so acronym-expanded substrate names do not fragment the field.
COF substrate extraction now also normalizes shorthand support wording such as `supported on ITO substrate` to `ITO glass`, so common film-growth substrate abbreviations stay queryable under the same canonical value.
COF catalyst extraction now normalizes common acid-catalyst abbreviations such as `AcOH`, `HOAc`, and `TFA` to canonical values like `acetic acid` and `trifluoroacetic acid`, so catalyst fields stay queryable across shorthand-heavy synthesis paragraphs.
COF base extraction now also normalizes shorthand base wording such as `Et3N`, `NEt3`, `TEA`, and `Hunig's base` to canonical values like `triethylamine` and `DIPEA`, so base fields stay queryable across abbreviation-heavy synthesis paragraphs.
COF solvent extraction now also normalizes shorthand solvent wording such as `MeCN`, `CH3CN`, `o-DCB`, and `n-BuOH` to canonical values like `acetonitrile`, `1,2-dichlorobenzene`, and `n-butanol`, so solvent-heavy synthesis paragraphs do not fragment the `solvents` field.
COF solvent extraction now also normalizes additional shorthand and expanded solvent wording such as `MeOH`, `EtOH`, `tetrahydrofuran`, `N,N-dimethylformamide`, and `N,N-dimethylacetamide` to canonical values like `methanol`, `ethanol`, `THF`, `DMF`, and `DMAc`, so mixed shorthand/full-name solvent wording stays queryable under one solvent vocabulary.
COF solvent extraction now also normalizes `DCM` and `CH2Cl2` to the canonical `dichloromethane` solvent value, so mixed shorthand/full-form dichloromethane wording does not split the `solvents` field.
COF route extraction now also normalizes hyphenated `vapor-induced conversion`, `vapour-induced conversion`, and the common `VIC` acronym to the canonical `vapor induced conversion` route value, so film-growth procedures do not fragment polymerization route fields.
COF interface extraction now also normalizes slash-form interface wording such as `air/water interface` and `liquid/liquid interface` to the canonical `air-water interface` and `liquid-liquid interface` values, so punctuation differences do not fragment interfacial growth records.
COF temperature extraction now also captures compact Celsius wording such as `120°C` from real open-access synthesis paragraphs, so temperatures are not missed when authors omit the space before `°C`.
COF route extraction now also preserves real-paper `Schiff base chemical reaction` wording as a polymerization route value, so open-access synthesis paragraphs that avoid the more specific condensation/polycondensation phrasing still contribute route evidence to the benchmark.
COF linkage extraction now also treats real-paper `imine-based COF` wording as the canonical `imine` linkage value, so open-access abstracts that state the route first and the linkage in a follow-up sentence still contribute linkage evidence to the benchmark.
COF time extraction now also captures hyphenated duration wording such as `7-day growth` from real open-access vapor-induced conversion procedures, so the main growth duration is retained alongside shorter furnace hold times in experimental schedule paragraphs.
MOF name extraction now also captures real-paper patterns such as `MIL-100 (Fe) is a highly porous metal-organic framework (MOF)` from open-access abstracts, so benchmark cases are not limited to the narrower `(MOF, Name)` and `metal-organic framework (MOF), Name` formulations.
COF temperature extraction now ignores standalone Kelvin measurement values in mixed synthesis/characterization abstracts, so real-paper sentences like `300 K` magnetic characterization do not leak into synthesis conditions while genuine `room-temperature` synthesis cues are preserved.
COF name extraction now ignores generic descriptive clauses such as `we here report on a new COF capable of ...` from real open-access abstracts, so synthesis summaries without an explicit framework identifier do not hallucinate long prose fragments as framework names.
COF paragraph extraction now keeps real open-access abstracts that provide linkage or condition evidence even when no explicit framework identifier is given, instead of dropping the record solely because the abstract names the material only as `the COF`.
COF name extraction now also preserves framework family notation from real open-access abstracts such as `imine-linked COFs, W-A-X (X = H, Cl, Br, I), was synthesized`, so descriptor-before-name plural wording does not drop valid synthesis names.
COF monomer extraction now also captures real open-access `Using A and B, a family of ... COFs was synthesized` wording, so descriptor-before-name abstracts such as the W-A-X paper retain monomer evidence instead of only the family name and linkage.
COF temperature extraction now ignores auxiliary precursor-powder setpoint temperatures when real vapor-induced conversion procedures also state the main furnace schedule, so side conditions like `80 °C (105 °C for BPyDCA, 110 °C for BPDA)` do not crowd out the synthesis temperatures that define the actual growth program.
MOF name extraction now also preserves direct framework identifiers in real experimental paragraphs such as `We prepared CaNDC-MOF using a solvothermal synthesis method`, so open-access procedures no longer require the `metal-organic framework (MOF)` descriptor scaffold before the synthesis name is kept.
COF atmosphere extraction now also preserves real-paper carrier-gas composition wording such as `hydrogen and argon flow ... used as carrier gas`, so open-access vapor-induced conversion procedures retain scoped gas-condition evidence instead of dropping it.
COF substrate extraction now also preserves explicit metal-surface wording such as `on Au(111)` from real open-access on-surface synthesis abstracts, so narrow experimental paragraphs still contribute substrate evidence even when they omit the usual solvent/temperature condition bundle.

## 2026-06-16 note

MOF name extraction now also preserves formula-style framework identifiers from real open-access summary paragraphs such as `The solvothermal reaction ... gave rise to a metal-organic framework (MOF), {(H 3 O + ) 2 [Ca(NDC)(C 2 H 5 O)(OH)]} 4 璺?.1H 2 O`, so route-first literature wording no longer drops the framework name when the descriptor introduces the identifier after the synthesis clause.
COF condition extraction now ignores workup-specific timings, room-temperature drying/cooling mentions, and wash/storage solvents when a real experimental procedure already states the main reaction hold, so open-access TFPT-COF procedures retain `120 °C`, `72 h`, `mesitylene`, and `1,4-dioxane` without leaking `15 min`, `DMF`, `THF`, or `DCM` from post-synthesis handling.
COF route extraction now also preserves real-paper `azomethine coupling` wording, and COF substrate extraction now recognizes decorated surface phrases such as `iodine-modified Au(111) surface`, so open-access on-surface porphyrin COF abstracts retain their core synthesis route and substrate evidence.
COF monomer extraction now trims trailing narrative verbs such as `... and investigated in detail ...` from coupling clauses, so real open-access abstracts no longer leak non-reagent prose into the `monomers` field.

MOF name extraction now also preserves formula-style framework identifiers from real open-access summary paragraphs such as `The solvothermal reaction ... gave rise to a metal-organic framework (MOF), {(H 3 O + ) 2 [Ca(NDC)(C 2 H 5 O)(OH)]} 4 路1.1H 2 O`, so route-first literature wording no longer drops the framework name when the descriptor introduces the identifier after the synthesis clause.

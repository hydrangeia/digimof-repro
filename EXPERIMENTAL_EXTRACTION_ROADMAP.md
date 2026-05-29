# MOF/COF 实验文献抽取路线

本文档记录后续抽取系统的设计取舍和候选实验文献。当前优先级是：先把 MOF 路线稳定复现，再把 COF 作为独立规则层搭上去。

## 1. 当前判断

短期不建议完全重写 DigiMOF。更稳的路线是：

1. 保留原始 DigiMOF/ChemDataExtractor 1.3.0 作为 MOF parser 内核。
2. 在外层维护 `framework_miner`，负责输入、输出、URL/PDF 处理、schema 统一、过滤和回归测试。
3. COF 后续另建规则层，不直接塞进 DigiMOF 的 MOF 规则里。COF 的关键字段和 MOF 不同，强行混合会让误识别变多。

这个设计的好处是原论文复现链路可解释，后续又能逐步替换或扩展，不会被旧 CDE 代码绑死。

## 2. MOF 稳定阶段候选文献

这些文章优先选开放 HTML/PMC 页面，因为网页正文比 PDF 更容易被旧 CDE 稳定解析。PDF 仍保留作为 fallback。

| 优先级 | 文献 | URL | 用途 |
| --- | --- | --- | --- |
| 1 | Synthesis, structure, and fluorescence properties of a calcium-based metal-organic framework | https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/ | 已用于 URL raw smoke test。实验段落明确给出 CaNDC-MOF、solvothermal、100 °C、7 days、配比、洗涤和干燥，适合测试公式型 MOF 名称与条件抽取。 |
| 2 | Facile and template-free solvothermal synthesis of mesoporous/macroporous metal-organic framework nanosheets | https://pubs.rsc.org/en/content/articlelanding/2018/ra/c8ra06576d | 摘要和实验描述都包含 solvothermal MOF nanosheets，适合测试形貌词、metal/ligand 起始物和批量网页段落处理。 |
| 3 | Solvothermal Synthesis of a Novel Calcium Metal-Organic Framework | 待重新核对开放全文 URL | 标题、实验和表征围绕单个 Ca-MOF，适合作为第二个 calcium 系列回归样本；`PMC8623775` 本轮试跑未产出 MOF 记录，暂不列入成功回归集。 |
| 4 | Synthesis of a metal-organic framework by plasma in liquid to increase reduced metal ions and enhance water stability | https://pubs.rsc.org/en/content/articlepdf/2021/ra/d1ra00942g | 包含 HKUST-1 与 plasma in liquid 方法，适合测试非传统合成路线词表。 |

## 3. COF 阶段候选文献

COF 阶段暂不抢跑实现，但可以先把 schema 和样本文献定下来。

| 优先级 | 文献 | URL / 本地路径 | 用途 |
| --- | --- | --- | --- |
| 1 | Synthesis of C-C Bonded Two-Dimensional Conjugated Covalent Organic Framework Films by Suzuki Polymerization on a Liquid-Liquid Interface | `D:\papers\cofs\Synthesis of C-C Bonded Two-Dimensional Conjugated Covalent Organic Framework Films by Suzuki Polymerization on a Liquid.pdf`; DOI: https://doi.org/10.1002/anie.201811399 | 用户给出的本地 PDF。适合 COF parser 的第一篇，因为它包含 2DCCOF1/2DCCOF2、Suzuki polymerization、Pd(PPh3)4、K2CO3、水/甲苯界面、2 °C、one month、pore size 和 stacking。 |
| 2 | Two-dimensional covalent organic framework films prepared on various substrates through vapor induced conversion | https://pmc.ncbi.nlm.nih.gov/articles/PMC8931112/ | 开放 HTML，适合测试 COF film、substrate、Schiff base polycondensation、vapor induced conversion。 |
| 3 | Integrated interfacial design of covalent organic framework photocatalysts to promote hydrogen evolution from water | https://pmc.ncbi.nlm.nih.gov/articles/PMC9852592/ | 开放 HTML，适合测试 COF 名称、光催化应用、Pt co-catalyst、HER 性能字段。 |
| 4 | Recent advances in room-temperature synthesis of covalent organic frameworks | https://pmc.ncbi.nlm.nih.gov/articles/PMC11912503/ | 综述，不作为实验抽取主样本，但适合整理 COF 合成路线词表：liquid-liquid interface、on-water surface、electrosynthesis、sonochemical、mechanochemical、photochemical、Suzuki coupling、Schiff-base、Knoevenagel 等。 |

## 4. COF schema 草案

COF 不建议复用 `MOF_data`，而是继续用 `framework_miner` 的通用字段：

```json
{
  "schema_version": "framework_miner/0.2",
  "framework_type": "COF",
  "source": {},
  "evidence_text": "",
  "fields": {
    "names": [],
    "linkages": [],
    "polymerization_routes": [],
    "monomers": [],
    "catalysts": [],
    "bases": [],
    "solvents": [],
    "interfaces": [],
    "temperature": [],
    "time": [],
    "substrates": [],
    "stacking": [],
    "pore_size": [],
    "properties": []
  }
}
```

第一版 COF parser 可以先从规则开始，不急着上 ChemDataExtractor v2：

- 名称：`COF`、`2DCCOF1`、`2DCCOF2`、`PyTTA-TPA-COF` 等。
- 键型/反应：`C-C bonded`、`sp2-carbon-linked`、`imine-linked`、`hydrazone`、`boronate ester`、`Suzuki polymerization`、`Schiff base polycondensation`。
- 实验条件：温度、时间、溶剂、界面、催化剂、碱、惰性气氛、洗涤/干燥。
- 材料结构：film、powder、2D/3D、stacking、pore size、substrate。

## 5. 下一轮验证队列

工具额度恢复后优先跑：

```powershell
$env:PYTHONPATH = ((Resolve-Path '.').Path + ';' + (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path)
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path

conda run -n digimof-repro pytest tests\test_framework_miner.py
conda run -n digimof-repro python -m framework_miner.cli sample_inputs -o sample_outputs\framework_miner_ntu105.jsonl --mof-only
conda run -n digimof-repro python -m framework_miner.cli https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/ -o sample_outputs\framework_miner_url_pmc9085643.jsonl --mof-only --max-chars 3000
```

当前这三步已经稳定。下一轮再扩展到第 2 和第 4 篇 MOF 文献；第 3 篇需要先重新核对开放全文 URL，最后再进入 COF parser。

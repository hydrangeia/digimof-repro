# DigiMOF 本地复现说明

本文档记录在 `H:\dongfx\tools\project\digimof` 中复现 DigiMOF 代码的过程。源码来自 `DigiMOF-database-master-main-main.zip`，论文为 `digimof-a-database-of-metal-organic-framework-synthesis-information-generated-via-text-mining.pdf`。

如果只是想日常使用，不想看完整复现过程，先看 `PERSONAL_USAGE_README.md`。

## 1. 项目做了什么

DigiMOF 的目标是从 MOF 文献正文中自动抽取合成相关信息，并整理成结构化数据库。论文中描述的整体流程是：

1. 使用 ChemDataExtractor 的网页抓取和文档解析能力，结合 CSD MOF subset，收集 MOF 相关论文 HTML/XML。
2. 对文章进行分句、分词、词性标注和化学实体识别。
3. 在 ChemDataExtractor 1.3.0 基础上增加面向 MOF 的规则解析器，抽取：
   - MOF 名称
   - 合成路线，如 solvothermal、hydrothermal、mechanochemical
   - 溶剂
   - organic linker
   - metal precursor
   - topology
4. 用正则和排除列表过滤非 MOF 误识别项。
5. 以 JSON Lines 形式保存抽取结果，后续可转为 CSV/Excel 再分析。

论文中给出的数据规模是：自动下载 43,281 篇唯一 MOF 文章，抽取 15,501 个唯一 MOF materials，并获得超过 52,680 条关联属性。论文还说明 parser 的开发方式是先在单句上调规则，再用小批随机文章迭代，最后在 50 篇未见过的 MOF 文章上评估 precision、recall 和 F-score。

## 2. 源码结构

解压后主要目录如下：

```text
DigiMOF-database-master-main-main/
  README.md
  requirements.txt
  chemdataextractor_MOFs/
    MOF_extract.py
    MOF_database.py
    json_to_csv.py
    chemdataextractor/
      model.py
      doc/text.py
      parse/
        mof_topology.py
        synthesis.py
        organic_precursor.py
    web-scrape/
    tests/
```

关键文件说明：

- `chemdataextractor_MOFs/chemdataextractor/`：仓库内置并修改过的 ChemDataExtractor 1.3.0，不应被新版 pip/conda 包覆盖。
- `chemdataextractor_MOFs/chemdataextractor/doc/text.py`：把 MOF parser 接入 `Paragraph` 和 `Caption`。
- `chemdataextractor_MOFs/chemdataextractor/parse/mof_topology.py`：拓扑规则，如 `rht`、`fcu`、`pcu`、`dia` 等。
- `chemdataextractor_MOFs/chemdataextractor/parse/synthesis.py`：合成方法和溶剂规则。
- `chemdataextractor_MOFs/chemdataextractor/parse/organic_precursor.py`：linker 和 metal precursor 规则。
- `chemdataextractor_MOFs/MOF_database.py`：把 CDE records 整理为 DigiMOF 输出格式，并用 MOF 名称正则过滤。
- `chemdataextractor_MOFs/MOF_extract.py`：批量遍历 HTML/XML 文件并调用 `MOFDataBase.extract()`。

注意：原始 `README.md` 中写的是 `extract.py`，但这个压缩包里实际入口是 `MOF_extract.py`。

## 3. 已创建的复现文件

本次复现新增了几个辅助文件：

```text
environment.yml
chemdataextractor-local.yml
sample_inputs/ntu105.html
sample_outputs/ntu105_demo.json
REPRODUCTION_README.md
```

- `environment.yml`：已验证可用的 conda 依赖。
- `chemdataextractor-local.yml`：把 ChemDataExtractor 模型目录固定到本项目的 `cde-data`。
- `sample_inputs/ntu105.html`：最小 HTML 样例。
- `sample_outputs/ntu105_demo.json`：样例运行得到的输出。

## 4. 创建 conda 环境

推荐使用 Python 3.8。不要用系统默认 Python 3.13，因为本项目代码使用了旧接口，例如 `collections.MutableSequence`，在新 Python 中会报错。

在 PowerShell 中进入工作区：

```powershell
cd H:\dongfx\tools\project\digimof
conda env create -f environment.yml
conda activate digimof-repro
```

如果环境已经存在，也可以按本次实际复现过程创建：

```powershell
conda create -y -n digimof-repro python=3.8 pip
conda install -y -n digimof-repro -c conda-forge appdirs pyyaml lxml beautifulsoup4 cssselect python-crfsuite nltk requests six pandas pdfminer.six pytest dawg selenium=3.141.0
```

`selenium` 对核心文本抽取不是必要算法依赖，但原代码 import HTML reader 时会间接 import Elsevier 抓取模块，因此需要补上它才能不改源码运行 `MOF_extract.py`。

## 5. 设置本地源码和模型目录

每次运行前设置两个环境变量：

```powershell
$env:PYTHONPATH = (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
```

验证导入的是仓库自带版本：

```powershell
conda run -n digimof-repro python -c "import chemdataextractor, sys; print(sys.version); print(chemdataextractor.__version__); print(chemdataextractor.__file__)"
```

期望看到：

```text
3.8.20 ...
1.3.0
...\DigiMOF-database-master-main-main\chemdataextractor_MOFs\chemdataextractor\__init__.py
```

## 6. 下载 ChemDataExtractor 模型

CDE 的分句、词性标注和化学实体识别依赖模型文件。因为旧 CLI 会 import 抓取模块并带来额外副作用，建议直接调用 `chemdataextractor.data`：

```powershell
$env:PYTHONPATH = (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
conda run -n digimof-repro python -c "from chemdataextractor.data import PACKAGES; [p.download() for p in PACKAGES]; print('done')"
```

模型会下载到：

```text
cde-data/models/
```

本次复现确认 18 个模型文件均存在，包括：

```text
cem_crf-1.0.pickle
cem_crf_chemdner_cemp-1.0.pickle
cem_dict-1.0.pickle
cem_dict_cs-1.0.pickle
clusters_chem1500-1.0.pickle
pos_crf_wsj_genia-1.0.pickle
punkt_chem-1.0.pickle
```

## 7. 运行最小样例

样例输入文件：

```text
sample_inputs/ntu105.html
```

运行：

```powershell
$env:PYTHONPATH = (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
conda run -n digimof-repro python -c "from MOF_extract import create_db; create_db(r'H:\dongfx\tools\project\digimof\sample_inputs', r'H:\dongfx\tools\project\digimof\sample_outputs', 0, 1, 'ntu105_demo')"
```

输出文件：

```text
sample_outputs/ntu105_demo.json
```

本次实际输出：

```json
{"MOF_data": {"file": "H:\\dongfx\\tools\\project\\digimof\\sample_inputs/ntu105.html", "synthesis_route": [{"synthesis": "solvothermal"}], "topology": "rht", "linker": [{"linker": "['hexacarboxylate']"}], "compound": {"Compound": {"names": ["NTU-105-NH2"]}}}}
```

说明环境已经能跑通核心链路：HTML -> ChemDataExtractor Document -> MOF parser -> JSON Lines。

## 8. 运行自己的 HTML/XML 文献

准备一个输入目录，例如：

```text
my_papers/
  paper_001.html
  paper_002.xml
```

准备输出目录：

```powershell
mkdir my_outputs
```

运行：

```powershell
$env:PYTHONPATH = (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
conda run -n digimof-repro python -c "from MOF_extract import create_db; create_db(r'H:\dongfx\tools\project\digimof\my_papers', r'H:\dongfx\tools\project\digimof\my_outputs', 0, 100, 'raw_data')"
```

参数含义：

- 第 1 个参数：HTML/XML 输入目录。
- 第 2 个参数：输出目录，必须提前存在。
- 第 3 个参数：起始文章索引。
- 第 4 个参数：结束文章索引，Python 切片语义，不包含该索引。
- 第 5 个参数：输出文件名，不含 `.json`。

输出是 JSON Lines，每行一条 MOF record。再次运行同一个文件名会追加写入，不会自动覆盖。

## 9. 推荐的新入口

为了不继续把新功能塞进原始 DigiMOF 目录，本次新增了一个轻量外壳：

```text
download_article_html.py
framework_miner/
  __init__.py
  legacy_digimof.py
  cli.py
tests/
  test_framework_miner.py
```

它仍然复用仓库内置的 DigiMOF/ChemDataExtractor 1.3.0 parser，但输出改成更稳定的 JSONL schema：

```json
{
  "schema_version": "framework_miner/0.1",
  "framework_type": "MOF",
  "source": {
    "id": "sample_inputs\\ntu105.html",
    "kind": "html",
    "element_index": 1
  },
  "evidence_text": "...",
  "fields": {
    "names": ["NTU-105-NH2"],
    "synthesis_routes": [{"synthesis": "solvothermal"}],
    "topologies": [{"abrv": "rht"}],
    "linker_routes": [{"linker": "['hexacarboxylate']"}]
  },
  "passes_mof_filter": true,
  "raw_records": [],
  "MOF_data": {}
}
```

优点：

- 不改原始 DigiMOF 源码。
- 同时保留 `fields`、`raw_records` 和旧格式 `MOF_data`。
- 保留 `evidence_text`，后面检查误抽取会容易很多。
- 支持文件、文件夹、PDF 和 URL。
- 默认会把同一段证据文本中的名称、合成路线、拓扑、linker 合并成一条记录。

运行本地 HTML/XML/PDF 文件夹：

```powershell
$env:PYTHONPATH = ((Resolve-Path '.').Path + ';' + (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path)
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
conda run -n digimof-repro python -m framework_miner.cli sample_inputs -o sample_outputs\framework_miner_ntu105.jsonl --mof-only
```

本次已验证该命令能从 `sample_inputs/ntu105.html` 生成 1 条合并后的 MOF 记录，包含 `NTU-105-NH2`、`solvothermal`、`rht` 和 linker。

运行 PDF：

```powershell
conda run -n digimof-repro python -m framework_miner.cli digimof-a-database-of-metal-organic-framework-synthesis-information-generated-via-text-mining.pdf -o sample_outputs\framework_miner_pdf_smoke.jsonl --pages 1 --max-chars 4000
```

本次已验证该 PDF smoke test 可运行，但 DigiMOF 论文本身是方法论文，不适合作为合成关系抽取样本。

运行网页 URL：

```powershell
conda run -n digimof-repro python -m framework_miner.cli https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/ -o sample_outputs\framework_miner_url_pmc9085643.jsonl --mof-only --max-chars 3000
```

URL 模式做了两件事：

- URL 请求优先直连并设置 User-Agent；如果直连失败再走系统代理。这样可以避开部分代理偶发中断或返回非正文内容的问题。
- 下载 HTML 后先用 BeautifulSoup 抽正文段落，并只把含 MOF / metal-organic framework / solvothermal 等信号的候选段落交给旧 CDE，避免整页导航、脚本、参考文献和 `.gov` 横幅吃掉 `--max-chars` 预算。
- 对明确写着 `metal-organic framework (MOF), ...` 或 `(MOF, NAME)` 的段落增加一条保守 heuristic 记录，弥补旧 DigiMOF 对某些公式型 MOF 名称过滤太窄的问题。这个兜底规则会尽量保留 `·1.1H2O` 这类公式名中的小数点，并在 `, was synthesized`、`;`、句号后接新句等边界处停止。

本次已验证：`https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/` 在 `--mof-only --max-chars 3000` 下可生成 1 条去重后的材料级 MOF 记录，包含公式型名称 `{(H 3 O + ) 2 [Ca(NDC)(C 2 H 5 O)(OH)]} 4 ·1.1H 2 O` 和 `solvothermal`。重复出现于摘要和实验短句中的同一材料会合并为一条记录，并保留 `evidence_texts`。

### 下载网页 HTML 到本地

如果不想每次都直接解析 URL，可以先把网页保存成本地 HTML：

```powershell
conda run -n digimof-repro python download_article_html.py https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/ -o downloaded_articles --overwrite
```

也可以准备一个 URL/DOI 列表文件，每行一个 URL 或 DOI，`#` 开头的行会被忽略：

```powershell
conda run -n digimof-repro python download_article_html.py --url-file urls.txt -o downloaded_articles
```

如果手里是一批 DOI，也可以单独使用 DOI 文件：

```powershell
conda run -n digimof-repro python download_article_html.py --doi-file dois.txt -o downloaded_articles
```

下载器会把裸 DOI 自动转成 `https://doi.org/...`，优先直连，失败后再走系统代理；输出包括网页文件和 `downloaded_articles/manifest.jsonl`。下载后的 HTML 可以直接作为本地输入解析：

```powershell
conda run -n digimof-repro python -m framework_miner.cli downloaded_articles -o sample_outputs\framework_miner_downloaded_articles.jsonl --mof-only --max-chars 3000
```

本次已验证：下载 `PMC9085643` 到 `downloaded_articles/` 后，本地解析可输出 1 条 Ca-MOF 记录。`downloaded_articles/` 默认写入 `.gitignore`，避免把论文网页全文提交到版本库。

## 10. 版本管理建议

本目录当前不是 git 仓库。GitHub connector 已能连接到账号 `hydrangeia`，本机 `git` 可用，但本机没有安装 GitHub CLI (`gh`)，而当前 GitHub connector 没有暴露“新建仓库/创建 fork”的接口。因此推荐流程是：

1. 在 GitHub 网页上新建一个空的 private repository，例如 `digimof-repro`。
2. 不要初始化 README、license 或 `.gitignore`，保持空仓库。
3. 回到本地执行：

```powershell
git init
git add .gitignore REPRODUCTION_README.md EXPERIMENTAL_EXTRACTION_ROADMAP.md environment.yml chemdataextractor-local.yml download_article_html.py run_pdf_examples.py classify_pdfs.py inspect_pdf_terms.py framework_miner tests sample_inputs sample_outputs/.gitkeep DigiMOF-database-master-main-main
git commit -m "Reproduce DigiMOF and add framework miner"
git branch -M main
git remote add origin https://github.com/hydrangeia/digimof-repro.git
git push -u origin main
```

`.gitignore` 已排除 `cde-data/`、`downloaded_articles/`、生成输出和压缩包。CDE 模型和论文网页可以按 README 重下，不建议提交。

## 11. PDF 示例

DigiMOF 原始入口主要面向 HTML/XML。仓库里有旧版 `PdfReader`，但本次直接用它读取整篇 PDF 时超过 120 秒未完成。更稳妥的做法是：先用 `pdfminer.six` 把 PDF 转成段落，再把段落送入 DigiMOF parser。

本次新增了辅助脚本：

```text
run_pdf_examples.py
```

运行单篇 PDF：

```powershell
$env:PYTHONPATH = ((Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path + ';' + (Resolve-Path '.').Path)
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
conda run -n digimof-repro python run_pdf_examples.py digimof-a-database-of-metal-organic-framework-synthesis-information-generated-via-text-mining.pdf sample_outputs\digimof_paper_pdf_demo.jsonl --pages 1 --max-chars 4000
```

运行一个 PDF 文件夹：

```powershell
conda run -n digimof-repro python run_pdf_examples.py my_pdf_papers sample_outputs\pdf_batch_demo.jsonl --pages 2 --max-chars 8000
```

只保留通过 DigiMOF MOF 名称过滤的记录：

```powershell
conda run -n digimof-repro python run_pdf_examples.py my_pdf_papers sample_outputs\pdf_mof_only.jsonl --pages 2 --mof-only
```

本次工作区只有一篇 PDF，即 DigiMOF 论文自身。它是方法论文，不是单篇 MOF 合成实验文献，所以前 1 页示例只抽到了 raw 化学实体记录：

```json
{"source_file": "digimof-a-database-of-metal-organic-framework-synthesis-information-generated-via-text-mining.pdf", "record": {"names": ["ML"]}}
```

这个结果反而说明了 PDF 路线的两个注意点：

- PDF 文本抽取会产生编码噪声，例如连字符和引用编号变成乱码。
- 方法论文/综述论文不一定包含 DigiMOF 规则期望的“MOF 名称 + 合成条件 + topology/linker”关系，最好用真实合成论文 PDF 测试。

如果要用几篇 PDF 举例，把 PDF 放进同一个目录，例如 `my_pdf_papers/`，再运行上面的文件夹命令即可。建议先用 `--pages 1` 或 `--pages 2` 小批量试跑，因为旧 CDE parser 对长 PDF 很慢。

## 12. 转 CSV

原始 `json_to_csv.py` 写死了作者本机路径，不能直接用。可以用下面的通用命令：

```powershell
conda run -n digimof-repro python -c "import pandas as pd; df=pd.read_json(r'H:\dongfx\tools\project\digimof\sample_outputs\ntu105_demo.json', lines=True); df.to_csv(r'H:\dongfx\tools\project\digimof\sample_outputs\ntu105_demo.csv', index=False)"
```

对于真实数据，把输入 JSON 和输出 CSV 路径换成自己的即可。

## 13. 已发现的坑

1. 原始 README 的入口名不准：应使用 `MOF_extract.py` 或直接 import `create_db()`。
2. `MOF_extract.py` 的 `__main__` 部分写死了 `DIRECTORY NAME`、`save/`、`FILENAME`，建议用 `python -c "from MOF_extract import create_db; ..."` 调用。
3. 必须让 `PYTHONPATH` 指向 `chemdataextractor_MOFs`，否则可能导入系统安装的 ChemDataExtractor，而不是仓库修改版。
4. `production.txt` 过宽，包含抓取、GUI、CSD API 等依赖；核心文本抽取只需要 `environment.yml` 中的依赖。
5. `csd-python-api` 属于 CCDC/CSD 生态，不是核心样例运行必需项。只有复现论文中 CSD 化学名处理和批量 CSD 流程时才需要额外配置。
6. CDE 模型文件必须下载，否则运行时会报 `ModelNotFoundError: Could not load ... Have you run cde data download?`
7. 旧代码会产生少量 warning，例如正则 `FutureWarning` 和旧写法 `SyntaxWarning`，本次验证中不影响抽取结果。
8. PDF 不是原始 DigiMOF 入口的主路径。可以通过 `run_pdf_examples.py` 跑，但速度和准确率明显依赖 PDF 文本质量。
9. 旧 DigiMOF 的 MOF 名称正则对某些真实 MOF 名称偏窄，例如公式型 calcium MOF；`framework_miner` 为网页段落增加了一个保守 heuristic，但后续仍应保留 evidence 做人工/程序校验。

## 14. 本次复现状态

已完成：

- 解压源码。
- 建立 `digimof-repro` conda 环境。
- 安装核心依赖。
- 下载 CDE 模型到 `cde-data`。
- 验证导入仓库自带 ChemDataExtractor 1.3.0。
- 运行最小 HTML 样例并生成 `sample_outputs/ntu105_demo.json`。
- 新增 `framework_miner` 外壳，并验证本地 HTML 样例可输出合并后的规范 JSONL。
- 新增 `download_article_html.py`，验证 `PMC9085643` 可下载为本地 HTML 并再次解析成功。
- 新增并执行 `tests/test_framework_miner.py`，当前 10 条测试通过，覆盖本地 NTU-105 集成抽取、网页候选段落过滤、公式型 MOF 名称、`metal–organic` / `metal organic` 写法、无 `raw_record` 合并兼容和材料级去重。
- 增加 PDF 辅助脚本并用本地 DigiMOF 论文 PDF 跑通 1 页示例，生成 `sample_outputs/digimof_paper_pdf_demo.jsonl`。
- 用 PMC9085643 MOF 网页验证 URL 合并模式可运行，生成 `sample_outputs/framework_miner_url_pmc9085643.jsonl`，输出 1 条去重后的 Ca-MOF 记录。
- 从本地论文核对了 DigiMOF 的方法和数据规模描述。

未做：

- 没有复现论文级别的 43,281 篇文章抓取流程。
- 没有配置 CCDC/CSD 的授权 API。
- 没有跑全量测试集；仓库测试多为脚本式验证，且部分期望值依赖旧版本模型/文本规范化细节。

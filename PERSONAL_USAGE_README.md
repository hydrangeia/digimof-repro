# 给自己看的 DigiMOF 使用说明

这份不是论文复现报告，而是日常怎么用、怎么理解这个文件夹。

## 0. 现在这个项目是什么

这里有两套东西：

1. `DigiMOF-database-master-main-main/`
   原始 DigiMOF 代码和它自带的旧 ChemDataExtractor。把它当作旧引擎，尽量不动。

2. `framework_miner/`、`download_article_html.py`、`tests/`
   我们自己加的外壳。以后主要用这部分。

一句话理解：原始 DigiMOF 负责“读句子并抽 MOF 信息”，我们新加的代码负责“把网页/PDF/本地文件喂得更稳，输出更好看，方便以后扩展 COF”。

## 1. 每次开始前先做什么

打开 PowerShell：

```powershell
cd H:\dongfx\tools\project\digimof
```

然后设置两个环境变量：

```powershell
$env:PYTHONPATH = ((Resolve-Path '.').Path + ';' + (Resolve-Path 'DigiMOF-database-master-main-main\chemdataextractor_MOFs').Path)
$env:CHEMDATAEXTRACTOR_CONFIG = (Resolve-Path 'chemdataextractor-local.yml').Path
```

这一步的意思是：

- 用本文件夹里的旧 ChemDataExtractor，不要误用系统里新的包。
- 告诉 ChemDataExtractor 模型文件在本地 `cde-data/`。

## 2. 最推荐的日常流程

推荐分两步：

1. 先把论文网页下载到本地。
2. 再从本地 HTML 批量抽取。

这样比每次直接解析 URL 稳，因为网页下载成功后，后面反复调 parser 不需要重复联网。

## 3. 下载一篇网页

例如 PMC 的开放全文：

```powershell
conda run -n digimof-repro python download_article_html.py https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/ -o downloaded_articles
```

下载结果会在：

```text
downloaded_articles/
```

同时会记录一个：

```text
downloaded_articles/manifest.jsonl
```

这个 manifest 记录原始输入、最终跳转到的网址、保存路径、文件大小等。

## 4. 批量下载 URL

新建一个 `urls.txt`，每行一个网页链接：

```text
https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/
https://pubs.rsc.org/en/content/articlelanding/2018/ra/c8ra06576d
```

运行：

```powershell
conda run -n digimof-repro python download_article_html.py --url-file urls.txt -o downloaded_articles
```

`#` 开头的行会被忽略，可以拿来写备注。

## 5. 批量下载 DOI

新建一个 `dois.txt`，每行一个 DOI：

```text
10.1039/D1RA00942G
10.1002/anie.201811399
```

运行：

```powershell
conda run -n digimof-repro python download_article_html.py --doi-file dois.txt -o downloaded_articles
```

也可以混着写 URL 和 DOI：

```powershell
conda run -n digimof-repro python download_article_html.py --url-file urls_or_dois.txt -o downloaded_articles
```

脚本会把裸 DOI 自动转成：

```text
https://doi.org/DOI
```

然后跟随跳转下载目标网页。

注意：DOI 跳转到哪里由出版社决定。有些 DOI 会跳到开放 HTML，有些会跳到摘要页或付费页。能不能抽到实验信息，取决于下载下来的页面里有没有正文。

## 6. 从本地 HTML 抽取 MOF 信息

下载完后运行：

```powershell
conda run -n digimof-repro python -m framework_miner.cli downloaded_articles -o sample_outputs\mof_results.jsonl --mof-only --max-chars 3000
```

参数怎么理解：

- `downloaded_articles`：输入文件夹。
- `-o sample_outputs\mof_results.jsonl`：输出文件。
- `--mof-only`：只保留看起来像 MOF 的记录。
- `--max-chars 3000`：每篇文章先只看候选段落里的前 3000 字，速度更稳。

如果结果太少，可以把 `--max-chars` 调大，例如：

```powershell
--max-chars 8000
```

但旧 ChemDataExtractor 比较慢，不建议一上来就喂整篇长文。

## 7. 直接解析 URL

也可以不下载，直接喂 URL：

```powershell
conda run -n digimof-repro python -m framework_miner.cli https://pmc.ncbi.nlm.nih.gov/articles/PMC9085643/ -o sample_outputs\mof_url_result.jsonl --mof-only --max-chars 3000
```

这个适合临时试一篇。正式做批量时，还是建议先下载。

## 8. 怎么看输出

输出是 JSONL，一行一个材料记录。重点看这几块：

```json
{
  "fields": {
    "names": ["NTU-105-NH2"],
    "synthesis_routes": [{"synthesis": "solvothermal"}],
    "topologies": [{"abrv": "rht"}],
    "linker_routes": [{"linker": "['hexacarboxylate']"}]
  },
  "evidence_texts": ["...原文证据..."]
}
```

日常优先看：

- `fields.names`：材料名。
- `fields.synthesis_routes`：合成方式。
- `fields.topologies`：拓扑。
- `fields.linker_routes`：linker。
- `evidence_texts`：它从哪句话判断出来的。

`evidence_texts` 很重要。后续人工检查、调规则、做 COF 时都靠它定位原因。

## 9. 测一下项目是否还正常

改代码后跑：

```powershell
conda run -n digimof-repro pytest tests -q -p no:cacheprovider --basetemp .pytest_tmp
```

现在应该看到类似：

```text
27 passed
```

如果只是旧 ChemDataExtractor 的 warning，一般不用管。

这里加 `--basetemp .pytest_tmp` 是为了避开 Windows 系统临时目录偶发的权限问题；`.pytest_tmp/` 已经在 `.gitignore` 里。

## 10. GitHub 怎么理解

现在已经有一个私有仓库：

```text
https://github.com/hydrangeia/digimof-repro
```

这个仓库是 private copy，不是严格意义上的 fork。因为 GitHub 上 public repo 一般不能直接 fork 成 private。

日常改完后：

```powershell
git status
git add .
git commit -m "写清楚这次做了什么"
```

如果当前网络允许 `git push`：

```powershell
git push
```

如果 `git push` 又连不上 GitHub，可以先只本地 commit。之后我可以继续用 GitHub API 帮你同步。

## 11. 什么东西不会进 GitHub

这些默认被 `.gitignore` 排除了：

- `cde-data/`：ChemDataExtractor 模型。
- `downloaded_articles/`：下载下来的论文网页。
- `sample_outputs/` 里的生成结果。
- `*.pdf`：论文 PDF。
- `*.zip`：压缩包。

原因很简单：代码和规则应该版本管理，论文全文、模型和生成数据不适合塞进 git。

## 12. 当前阶段的判断

现在最稳的路线是：

1. 先把 MOF 抽取流程稳定下来。
2. 多找几篇实验 MOF 文章做回归样例。
3. 再单独设计 COF 的 schema 和规则。

COF 不建议硬塞进 DigiMOF 原规则里。COF 的关键词、反应、linkage、monomer、catalyst、interface 和 MOF 不一样，应该作为 `framework_type = "COF"` 的新分支来做。

## 13. 现在怎么试 COF

现在已经有第一版很轻量的 COF 规则层，主要抓：

- COF 名称，例如 `2DCCOF1`、`2DCCOF2`、`PyTTA-TPA-COF`。
- linkage/键型，例如 `C-C bonded`、`imine-linked`、`hydrazone-linked`、`boronate ester`、`olefin-linked`、`beta-ketoenamine-linked`。
- 聚合/合成路线，例如 `Suzuki polymerization`、`Schiff base polycondensation`、`hydrazone formation`、`boronate ester condensation`、`Knoevenagel condensation`、`Schiff-base condensation`。
- monomer 候选，例如 `aryl diboronic ester`、`porphyrin monomer`、`PyTTA`、`TPA`，也支持带多个逗号的长单体名。
- 催化剂、碱、溶剂、界面。
- 温度和时间，包括 `room temperature`、`ambient temperature`、`overnight` 和 `three days` 这类文字表达。

跑内置 COF 小样例：

```powershell
conda run -n digimof-repro python -m framework_miner.cli sample_inputs\cof_suzuki.html -o sample_outputs\framework_miner_cof_suzuki.jsonl --framework cof --max-chars 3000
```

输出会像这样：

```json
{
  "framework_type": "COF",
  "fields": {
    "names": ["2DCCOF1", "2DCCOF2"],
    "polymerization_routes": [{"route": "Suzuki polymerization"}],
    "linkages": [{"linkage": "C-C bonded"}],
    "monomers": [
      {"monomer": "aryl diboronic ester", "role": "from"},
      {"monomer": "porphyrin monomer", "role": "from"}
    ],
    "catalysts": [{"catalyst": "Pd(PPh3)4"}],
    "bases": [{"base": "K2CO3"}],
    "interfaces": [{"interface": "water/toluene interface"}],
    "temperature": ["2 °C"],
    "time": ["one month"]
  }
}
```

如果要跑自己下载的 COF 网页：

```powershell
conda run -n digimof-repro python -m framework_miner.cli downloaded_articles -o sample_outputs\cof_results.jsonl --framework cof --max-chars 5000
```

如果一个文件夹里 MOF 和 COF 都有，可以跑：

```powershell
conda run -n digimof-repro python -m framework_miner.cli downloaded_articles -o sample_outputs\framework_results.jsonl --framework all --framework-only --max-chars 5000
```

目前 COF 还是 heuristic parser。它适合帮我们快速筛实验句子和抽取骨架，不适合把每个字段都当作最终数据库直接信任。现在已经覆盖 Suzuki、imine/Schiff-base、hydrazone、boronate ester、Knoevenagel 和 beta-ketoenamine 这几类核心合成骨架；后面最值得继续加的是真实开放文献样例、monomer normalization 和错误报告。

### COF monomer 字段怎么理解

`monomers` 里每个元素长这样：

```json
{"monomer": "aryl diboronic ester", "role": "from"}
```

其中：

- `monomer` 是从原文里截出来的候选单体名。
- `role` 表示它是怎么被抓到的。

现在有这些 `role`：

- `from`：来自 `synthesized from A and B`。
- `between`：来自 `formed between A and B`。
- `condensation`：来自 `condensation of A with B`。
- `polycondensation`：来自 `polycondensation of A with B`。
- `explicit`：来自 `monomers were A and B` 或 `monomers: A and B`。

这个字段现在故意保守：它不做复杂化学命名标准化，只保留原文候选片段。原因是 COF 单体名经常很长，括号、逗号、缩写很多，太早标准化容易把信息弄坏。后面如果要做设计数据库，再单独加一层 monomer normalization。

几个已经测试过的句型：

```text
2DCCOF1 and 2DCCOF2 were synthesized from aryl diboronic ester and porphyrin monomer by Suzuki polymerization.
```

会抽到：

```json
[
  {"monomer": "aryl diboronic ester", "role": "from"},
  {"monomer": "porphyrin monomer", "role": "from"}
]
```

```text
PyTTA-TPA-COF was obtained by Schiff base polycondensation of PyTTA with TPA.
```

会抽到：

```json
[
  {"monomer": "PyTTA", "role": "polycondensation"},
  {"monomer": "TPA", "role": "polycondensation"}
]
```

目前不建议把 `monomers` 当成 100% 正确结果。更好的用法是：先用它筛选和定位，再看 `evidence_texts` 核对原文。

## 14. 怎么判断它是不是真的变准了

现在加了一个很小的 benchmark：

```text
benchmark/gold_cases.jsonl
evaluate_framework_miner.py
```

它的目的不是追求数量，而是守住几个核心合成字段：

- MOF：材料名、合成路线、topology、linker。
- COF：材料名、polymerization route、linkage、monomer、catalyst/base、interface、temperature、time。

运行：

```powershell
conda run -n digimof-repro python evaluate_framework_miner.py
```

当前应该看到：

```text
cases: 8/8 passed
field recall: 64/64
```

它还会生成：

```text
benchmark/results.json
benchmark/results.md
```

怎么理解：

- `cases` 是样例级别，通过表示这一条文献片段的预期字段都命中了。
- `field recall` 是字段级别，例如 64/64 表示 64 个期望字段都抽到了。
- 如果某个字段漏了，`missing` 里会列出来。

为什么做这个：

我们现在更重视“少而准”。每次加规则前后都跑 benchmark，可以避免为了多抽一点东西，反而把原来已经准的核心字段弄坏。

后面真正产品化时，应该继续往 `benchmark/gold_cases.jsonl` 里加真实开放文献的短片段和人工预期字段。每加一种 COF 合成路线，比如 Knoevenagel、boronate ester、hydrazone，都先补一个 gold case，再改规则。

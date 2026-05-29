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
conda run -n digimof-repro pytest tests -q
```

现在应该看到类似：

```text
16 passed
```

如果只是旧 ChemDataExtractor 的 warning，一般不用管。

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
- linkage/键型，例如 `C-C bonded`、`imine-linked`。
- 聚合/合成路线，例如 `Suzuki polymerization`、`Schiff base polycondensation`。
- 催化剂、碱、溶剂、界面。
- 温度和时间。

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

目前 COF 还是第一版 heuristic。它适合帮我们快速筛实验句子和抽取骨架，不适合当作最终数据库直接信任。后面最值得继续加的是 monomer 识别和更多 linkage/route 词表。

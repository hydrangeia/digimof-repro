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
- `interfaces`
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
cases: 8/8 passed
field recall: 64/64
27 passed
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

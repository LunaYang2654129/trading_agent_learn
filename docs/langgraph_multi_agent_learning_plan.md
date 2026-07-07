# 基于 LangGraph 的股票多智能体系统学习与开发计划

## 学习目标

按会议纪要，第一版目标是构建一个 7 节点股票综合分析系统：`Planner Node` 统一调度，`Company/Financial/News/Technical` 四个专业 Agent 并行执行，`Decision Agent` 汇总初判，`Reflection Agent` 校验并决定 `Retry` 或 `Final Report`。

第一版不做自动交易、不接 broker、不输出真实下单指令。FinRL、DRL、回测和目标权重作为二期扩展。

## 阶段 0：理解会议架构

时间：1-2 天

目标：

- 明确 7 个 LangGraph 节点的职责边界。
- 明确 Planner、Decision 只是调度和中转，不属于业务专业分析 Agent。
- 明确专业业务 Agent 是 Company、Financial、News、Technical、Reflection。
- 明确 Retry 闭环必须由 Reflection 给出具体补采任务。

产出：

- `StockAnalysisState` 字段清单。
- 每个 Agent 的 JSON 输出 schema。
- 一份标准化最终报告目录。

## 阶段 1：LangGraph 基础

时间：3-5 天

重点：

- `StateGraph`
- `Node`
- `Edge`
- 条件路由
- 并行节点汇总
- checkpoint 断点续跑

练习：

- 写一个最小图：Start -> Planner -> Decision -> End。
- 增加条件路由：Reflection 通过则 End，不通过则回 Planner。
- 增加 checkpoint，模拟中断后恢复。

## 阶段 2：Mock 版 7 节点工作流

时间：1 周

目标：

- 不接真实外部数据，先用 mock 数据跑通完整链路。
- 验证四个专业 Agent 能并行写入全局 State。
- 验证 Decision 能读取四类结果生成初步研判。
- 验证 Reflection 能发现缺失项并触发 Retry。

任务：

- 实现 `planner_node`。
- 实现 `company_agent_node`。
- 实现 `financial_agent_node`。
- 实现 `news_agent_node`。
- 实现 `technical_agent_node`。
- 实现 `decision_agent_node`。
- 实现 `reflection_agent_node`。
- 实现 `final_report_node`。

验收：

- 输入一只股票代码和分析需求，可以生成报告。
- 人为删除某个字段后，Reflection 能触发 Retry。
- 超过 `max_retries` 后能停止并报告失败原因。

## 阶段 3：专业 Agent 数据接入

时间：1-2 周

### Company Agent

学习重点：

- 公司主营业务
- 行业赛道
- 股权结构
- 竞争地位

产出：

- `company_profile` schema。
- 公司资料来源记录。

### Financial Agent

学习重点：

- 年报/季报字段
- 净利润
- ROE
- 资产负债率
- 毛利率
- 现金流质量

产出：

- `financial_metrics` schema。
- 指标计算函数。

### News Agent

学习重点：

- 新闻检索
- 行业政策
- 券商研报
- 舆情利好/利空分类

产出：

- `news_sentiment` schema。
- 新闻来源和时间戳记录。

### Technical Agent

学习重点：

- K 线行情
- 成交量
- MACD
- PE/PB
- 趋势和支撑阻力

产出：

- `technical_indicators` schema。
- 技术指标计算函数。

## 阶段 4：Decision 与 Reflection 强化

时间：1 周

Decision Agent 目标：

- 汇总四类专业分析。
- 输出风险评分。
- 输出基础投资研判。
- 明确支持因素、风险因素和不确定项。

Reflection Agent 目标：

- 检查数据是否完整。
- 检查分析逻辑是否矛盾。
- 检查风险评估是否片面。
- 检查关键行业信息是否缺失。
- 输出 `passed`、`missing_items`、`contradictions`、`retry_tasks`。

验收：

- Reflection 不能只写“需要补充”，必须给 Planner 可执行的补采任务。
- 每次 Retry 都要更新 `retry_count` 和 `audit_log`。
- Retry 不能无限循环。

## 阶段 5：最终报告与审计

时间：3-5 天

报告结构：

- 股票与用户需求摘要。
- 公司基本面分析。
- 财务指标分析。
- 新闻与舆情分析。
- 技术指标分析。
- 综合风险评分。
- 初步研判结论。
- Reflection 校验结论。
- 数据来源与缺失项说明。
- 风险提示。

审计要求：

- 每个 Agent 输出都保留时间戳。
- 每个关键结论都能追溯到 State 字段。
- 每次 Retry 的原因和补采任务都写入 `audit_log`。

## 阶段 6：批量分析与稳定性

时间：1 周

目标：

- 支持批量股票分析。
- 每只股票独立 checkpoint。
- 单只失败不影响整个批次。
- 可恢复长任务。

验收：

- 批量输入 5 只股票，能分别输出 5 份报告。
- 中途停止后重启，可以从 checkpoint 继续。
- 失败样例能输出失败原因和已完成节点。

## 阶段 7：二期扩展

第一版稳定后，再考虑引入此前下载的 FinRL、FinRL-Meta、FinRL-X、TradingAgents 资料：

- 增加回测验证节点。
- 增加目标权重输出。
- 增加组合级风险控制。
- 增加历史决策记忆和后验表现反思。
- 引入 FinRL/DRL 作为候选量化信号，而不是直接替代 Decision。
- 引入 TradingAgents 式 bull/bear debate，但只作为 Decision 前的可选研究增强。

## 推荐里程碑

1. 第 1 周：完成会议架构接口冻结和 LangGraph Mock Demo。
2. 第 2 周：完成四个专业 Agent 的真实数据接入。
3. 第 3 周：完成 Decision、Reflection、Retry 闭环和最终报告。
4. 第 4 周：完成 checkpoint、批量分析、审计日志和样例报告集。

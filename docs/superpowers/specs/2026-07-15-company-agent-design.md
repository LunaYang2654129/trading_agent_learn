# Company Agent 并行分析模块设计

## 目标

在不修改 Data Layer、Technical Agent、Planner Agent 和 Decision Agent 的前提下，完善现有 Company Agent，使其成为 Technical Agent 的并行专业分析模块。Company Agent 使用项目现有 LLM 接口和独立 Prompt，输出稳定 JSON，覆盖商业模式、行业地位、竞争优势、财务健康、成长性和风险因素六个维度，并提供单独测试。

本轮新增独立的 Company–Technical 并行分析链。该链运行到两个专业结果汇合为止；Decision、Reflection 和最终报告保留为总体架构中的后续消费者，但本轮不接线。

## 约束

- 不修改已有 Data Layer。
- 不修改或影响 Technical Agent 及其工具和现有单链。
- 不修改 Planner Agent、Decision Agent。
- Company Agent 必须使用现有 `get_agent_llm("company")` 接口。
- Company Agent Prompt 继续存放在 `src/multiple_agent_finance/prompts/`。
- Company Result 必须是可校验、可序列化的统一 JSON。
- 必须提供独立的 `tests/test_company_agent.py`。
- Reflection Agent 仅在确有必要时修改；本轮并行链不进入 Reflection，因此不修改。
- 不输出真实交易订单或买卖指令。

## 当前实现

项目已有以下 Company Agent 占位代码：

- `agents/company.py`：调用 `get_company_profile`，将结果写入 `company_profile`。
- `tools/company_tools.py`：通过 yfinance 获取公司简介和少量风险信息。
- `prompts/company.md`：描述公司画像职责，但运行时没有加载。

占位实现没有调用 LLM，没有结构化 schema，也没有完整覆盖六个基本面维度。Technical Agent 当前采用 `StockAnalysisState + tool + audit_event` 的节点结构；实际共享 LLM 调用模式可参考 Reflection Agent 的 `get_agent_llm()` 用法。

## TradingAgents 参考与取舍

参考仓库：`TauricResearch/TradingAgents`。

采用的模式：

- Fundamentals Analyst 拥有明确的专业角色、Prompt 和基本面工具集合。
- ticker、分析日期和标的身份进入 Prompt，约束数据时间边界。
- 专业报告写入共享 Agent State，供下游节点消费。
- Pydantic schema 用于稳定输出；结构化调用失败时存在明确降级路径。
- 工具接口把基本面查询与 Agent 推理分离，并携带当前分析日期。
- 测试同时覆盖结构化成功路径和 provider 不支持结构化输出的 fallback。

不直接采用的部分：

- 上游 Fundamentals Analyst 主要输出自然语言报告；本项目要求机器可读 JSON。
- 上游分析师在当前 Graph Setup 中按执行计划顺序连接；本项目按目标架构让 Company 与 Technical 真正并行。
- 上游包含多空辩论、交易员和投资组合经理；这些不属于本次 Company Agent 范围。
- 上游 free-text fallback 可直接向下游传递文本；本项目必须把任何 fallback 归一化为 Company JSON。

## 目标架构

```text
用户输入
   ↓
Planner Agent（复用，不修改）
   ↓
┌─────────────────────────────────────────────┐
│ Parallel Multi-Agent Layer                  │
│                                             │
│ Technical Agent          Company Agent      │
│ （不修改）               （本轮完善）        │
│      ↓                        ↓             │
│ Technical Result        Company Result      │
└─────────────────────────────────────────────┘
   ↓
Result Collector
   ↓
parallel_analysis_result
   ⋮
Decision Agent（后续接入，本轮不修改）
   ↓
Reflection Agent → Confidence Route → Report/Retry
```

Company Agent 还具有以下只读或追加关系：

```text
Company Tools ──────────────→ Company Agent
Knowledge Base references ─→ Company Agent
Shared Memory references ──→ Company Agent
Company Agent ──追加引用───→ Shared Memory references
```

## 为什么本轮不接入 Decision

现有 Decision 的 `full` 模式要求 Company、Financial、News、Technical 四类结果；`technical` 模式只消费 Technical。若本轮仅将 Company 和 Technical 接入 Decision：

- `full` 模式会把 Financial 和 News 判定为缺失并降低置信度；
- `technical` 模式会忽略 Company Result；
- 解决该问题需要修改 Decision 或增加新的 Planner/chain mode，违反本轮边界。

因此本轮新链以 `parallel_analysis_result` 为稳定交付物，明确预留 Decision 下游接口。

## 组件设计

### CompanyAnalysis Schema

新增 `agents/company_schema.py`，使用 Pydantic 定义 Company Result。Schema 负责：

- 固定六个分析维度和兼容字段。
- 限制 `confidence` 在 `0.0` 到 `1.0`。
- 限制枚举值，例如 `status`、风险严重度和优势持续性。
- 将缺失列表、空值和弱模型常见占位字符串归一化。
- 提供 `model_dump(mode="json")` 结果，确保 State 和审计日志可序列化。

建议模型：

```python
class CompetitiveAdvantage(BaseModel):
    advantage: str
    durability: Literal["low", "medium", "high", "unknown"]
    evidence: str


class RiskFactor(BaseModel):
    risk: str
    severity: Literal["low", "medium", "high", "unknown"]
    evidence: str


class CompanyAnalysis(BaseModel):
    ticker: str
    as_of_date: str | None
    company_name: str
    status: Literal["success", "degraded"]
    business_model: dict
    industry_position: dict
    competitive_advantages: list[CompetitiveAdvantage]
    financial_health: dict
    growth: dict
    risk_factors: list[RiskFactor]
    confidence: float
    warnings: list[str]
    sources: list[dict]

    # 与现有 Decision 和存储代码兼容的别名。
    business_summary: str
    sector: str
    industry: str
    main_products: list[str]
    competitive_position: str
    key_risks: list[str]
```

嵌套分析对象的固定字段如下：

```json
{
  "business_model": {
    "summary": "",
    "products_services": [],
    "revenue_drivers": [],
    "evidence": []
  },
  "industry_position": {
    "sector": "",
    "industry": "",
    "position": "",
    "market_position_evidence": []
  },
  "financial_health": {
    "assessment": "",
    "strengths": [],
    "concerns": [],
    "evidence": []
  },
  "growth": {
    "assessment": "",
    "growth_drivers": [],
    "constraints": [],
    "evidence": []
  }
}
```

### Company Tools

完善现有 `tools/company_tools.py`，但不修改 Data Layer。工具层只负责收集和归一化证据，不负责最终定性判断。

证据包括：

- 公司名称、简介、行业、板块、产品和网站。
- 市值和估值辅助字段。
- 高层财务健康字段，例如现金、债务、利润率、现金流和流动性；缺失时保留 `None`。
- 高层成长字段，例如收入增长、盈利增长和分析师增长预期；缺失时保留 `None`。
- `warnings` 和 `sources`。

Company Tools 不生成买卖建议，不以当前时间覆盖 `as_of_date`，不伪造不可用字段。

### Company Agent

保留公开节点名 `company_agent_node(state)`，避免破坏现有导入。节点步骤：

1. 标准化 ticker。
2. 优先读取 `state.company_data`。
3. `company_data` 不存在时调用 `get_company_profile(ticker, as_of_date=...)`。
4. 读取 `planner_tasks.company`、`knowledge_base_refs` 和 `shared_memory_refs`。
5. 从 `prompts/company.md` 以 UTF-8 加载系统 Prompt。
6. 构造只含必要证据的 LLM 输入。
7. 调用 `get_agent_llm("company")`。
8. 校验并归一化 CompanyAnalysis。
9. 返回 `company_profile`、shared-memory 引用和 audit event。

节点输出：

```python
{
    "company_profile": company_result,
    "shared_memory_refs": [
        {"agent": "company_agent", "key": "company_profile"}
    ],
    "audit_log": [
        audit_event("company_agent", message, company_result)
    ],
}
```

### LLM 调用和降级

LLM 调用分三层：

1. 优先使用 `llm.with_structured_output(CompanyAnalysis)`。
2. provider 不支持或结构化调用失败时，用同一 LLM 普通调用，提取响应中的 JSON 对象并由 Pydantic 校验。
3. 普通调用失败、返回空内容或 JSON 仍无效时，根据工具证据生成确定性的 `status="degraded"` 结果。

fallback 始终返回相同 schema，不能把自由文本直接写入 `company_profile`。Company Agent 的失败不得抛出到并行图并丢失 Technical Result。

### Prompt

修改 `prompts/company.md`，要求：

- 分别分析六个指定维度。
- 只使用输入证据，不补造事实和精确数字。
- 每个重要结论必须包含证据。
- 把 `as_of_date` 视为信息截止日期。
- 数据不足时使用 `insufficient_evidence` 并写入 warning。
- 输出必须符合 CompanyAnalysis JSON。
- 不生成最终投资结论、买卖评级或交易订单。

Prompt 运行时输入：

- `ticker`
- `as_of_date`
- `user_request`
- `planner_tasks.company`
- `company_data`
- `knowledge_base_refs`
- `shared_memory_refs`

### 并行图

新增 `graph/company_technical_parallel.py`：

```text
START
  ↓
Planner
  ├────────────→ Technical Agent ────┐
  └────────────→ Company Agent ──────┤
                                      ↓
                               Result Collector
                                      ↓
                                     END
```

Result Collector 只有在两个专业节点都完成后执行，返回：

```json
{
  "ticker": "AAPL",
  "as_of_date": "2026-07-15",
  "technical_result": {},
  "company_result": {},
  "warnings": []
}
```

该结果写入 `state.parallel_analysis_result`。Technical Result 在外层封装，Technical Agent 本身不变。

### State

仅扩展 `StockAnalysisState` 类型声明：

```python
company_data: dict[str, Any]
parallel_analysis_result: dict[str, Any]
```

这不会改变 Data Layer 的生产逻辑，也不会改变现有字段语义。

## 数据流

### 预加载数据路径

```text
Data Layer
  ↓ company_data / market_data
StockAnalysisState
  ├→ Technical Agent → technical_indicators
  └→ Company Agent → company_profile
                         ↓
                  parallel_analysis_result
```

### Company Tool fallback 路径

```text
State 未包含 company_data
  ↓
Company Agent
  ↓
Company Tools
  ↓
标准化公司证据
  ↓
LLM + CompanyAnalysis Schema
```

## 错误处理

- `company_data` 缺失：使用 Company Tool fallback。
- Company Tool 失败：生成包含错误 warning 的降级证据。
- 数据源返回空值：保留 `None` 或空列表，不推测。
- LLM API 未配置：返回 `status="degraded"`，保留工具证据和警告。
- structured output 不受支持：普通 LLM JSON 路径重试一次。
- LLM 返回 Markdown code fence：只提取其中 JSON 对象。
- JSON 缺字段或类型错误：Pydantic 校验失败后进入确定性 fallback。
- 无来源的精确结论：不进入最终结果，并添加 warning。
- Company 分支异常：节点内部吸收为降级结果，Technical 分支继续运行。
- 并行结果 warning：汇总 Company 和 Technical 各自 warnings，不覆盖原字段。

## Reflection Agent 决策

本轮不修改 Reflection Agent。原因：

- 新并行链在专业结果汇合后结束，不调用 Decision 或 Reflection。
- 现有 Reflection 的职责与当前 technical/full 两种模式绑定。
- 现在增加 Company 校验会要求同步增加新的 chain mode 或改变 Decision 缺失项逻辑。

未来完整四专业 Agent 主图恢复时，Reflection 应增加：六维完整性、证据覆盖、风险严重度、置信度与数据完整度一致性检查。

## 测试设计

新增 `tests/test_company_agent.py`，完全使用受控 fixture 和 fake LLM，不依赖在线 API。

### Schema 测试

- 六个分析维度均为必需字段。
- `confidence` 超出 `0–1` 时校验失败或按明确规则归一化。
- 风险严重度和优势持续性只接受枚举值。
- 输出可用 `json.dumps` 序列化。
- Decision 兼容字段始终存在。

### Company Agent 测试

- 优先使用 `state.company_data`，不调用 fallback 工具。
- 缺少 `company_data` 时调用 Company Tool。
- Prompt 包含 ticker、as_of_date、Planner company task 和证据。
- 使用 `get_agent_llm("company")`。
- 结构化 LLM 返回有效 CompanyAnalysis 时写入 `company_profile`。
- provider 不支持 structured output 时调用普通 LLM JSON 路径。
- 普通响应含 code fence 时能够解析 JSON。
- 空响应、非法 JSON和 LLM 异常时返回完整降级 schema。
- 降级结果不含虚构数值或买卖建议。
- 返回 shared-memory 引用和 company audit event。

### 并行图测试

- 图包含 Planner、Technical、Company 和 Result Collector。
- Planner 同时扇出到 Technical 与 Company。
- 使用预加载 market/company fixture 可运行到 END。
- `parallel_analysis_result` 同时包含 `technical_result` 和 `company_result`。
- Company 进入降级路径时仍保留 Technical Result。

### 回归测试

- 现有 `tests/test_technical_agent.py` 全部通过。
- 现有 `tests/test_scaffold_imports.py` 对旧图的节点断言不变。
- 运行完整 `pytest -q`，确认 Data Layer、Technical、Planner、Decision 和旧图未受影响。

## 文件规划

新增：

- `src/multiple_agent_finance/agents/company_schema.py`
- `src/multiple_agent_finance/graph/company_technical_parallel.py`
- `tests/test_company_agent.py`

修改：

- `src/multiple_agent_finance/agents/company.py`
- `src/multiple_agent_finance/tools/company_tools.py`
- `src/multiple_agent_finance/prompts/company.md`
- `src/multiple_agent_finance/graph/state.py`

明确不修改：

- Data Layer 全部文件。
- `src/multiple_agent_finance/agents/technical.py`
- `src/multiple_agent_finance/tools/technical_tools.py`
- `src/multiple_agent_finance/agents/planner.py`
- `src/multiple_agent_finance/agents/decision.py`
- `src/multiple_agent_finance/graph/builder.py`
- `src/multiple_agent_finance/graph/technical_chain.py`
- `src/multiple_agent_finance/agents/reflection.py`

## 完成标准

- Company Result 稳定覆盖六个基本面维度。
- Company Agent 使用现有 LLM 和 Prompt 目录。
- Company 与 Technical 在独立图中并行执行并汇合。
- Technical Agent 和现有技术链没有代码变化。
- Data Layer、Planner 和 Decision 没有代码变化。
- LLM、数据源或 JSON 失败时仍返回明确的降级 JSON。
- `tests/test_company_agent.py` 独立通过。
- 完整测试套件通过。
- 最终报告列出新增文件、修改文件、调用流程、测试命令及实际结果，并解释 Reflection Agent 未修改的原因。

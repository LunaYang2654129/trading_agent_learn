# Company Agent 并行分析模块最终说明

本文档用于说明 `company-agent` 分支中 Company Agent 的最终实现、Prompt 后期调整、并行调用流程，以及常用运行和测试指令。

## 1. 当前 Company Agent 并行流程

当前 Company Agent 与 Technical Agent 的并行分析流程为：

```text
Planner Agent
     │
     ├──> Technical Agent ──> Technical Result
     │
     └──> Company Agent   ──> Company Result
                                  │
Technical Result ─────────────────┤
                                  ↓
                           Result Collector
                                  ↓
                    parallel_analysis_result
```

说明：

- Planner Agent 负责生成 Technical 与 Company 两类分析任务。
- Technical Agent 使用预加载的 `market_data` 计算趋势、成交量、MACD、RSI 和支撑阻力等指标。
- Company Agent 使用预加载的 `company_data`，或通过 Company Tool 获取公司资料。
- Company Agent 通过项目现有 LLM 接口完成基本面分析。
- Result Collector 在两个并行节点都结束后汇总结果和 warnings。
- 并行图最终输出 `parallel_analysis_result`，供后续 Decision Agent 使用。

本次没有把并行结果接入现有 Decision Agent 和 Reflection Agent，也没有修改原有 Planner、Decision、Reflection 或 Technical 单链路。

## 2. Company Agent 调整内容

### 2.1 六维 Company Result

Company Agent 固定分析六个维度：

- 商业模式；
- 行业地位；
- 竞争优势；
- 财务健康；
- 成长性；
- 风险因素。

最终结果使用 `CompanyAnalysis` Pydantic Schema 校验，主要输出字段包括：

- `ticker`
- `as_of_date`
- `company_name`
- `status`
- `business_model`
- `industry_position`
- `competitive_advantages`
- `financial_health`
- `growth`
- `risk_factors`
- `confidence`
- `warnings`
- `sources`

同时保留现有代码兼容字段：

- `business_summary`
- `sector`
- `industry`
- `main_products`
- `competitive_position`
- `key_risks`

### 2.2 公司证据读取顺序

Company Agent 优先读取：

```text
state.company_data
```

如果 State 中没有预加载公司数据，才调用：

```python
get_company_profile(ticker, as_of_date=as_of_date)
```

这样可以让上游 Data Layer 或外部数据适配器只采集一次数据，Company Agent 直接消费标准化结果，避免每个 Agent 重复请求 Yahoo。

### 2.3 数据时点判断

最终 Prompt 明确区分：

- `as_of_date`：分析信息截止日期；
- `period_end`：财报数据覆盖期末；
- `filed_at`：财报或公告公开日期；
- 最新市场数据日期；
- 当前 yfinance company snapshot。

当前 snapshot 不能自动证明历史 `as_of_date` 的公司状态。如果无法完成 point-in-time 验证，Company Agent 必须：

- 只保留输入中仍可验证的事实；
- 添加 point-in-time warning；
- 降低 `confidence`；
- 不把当前快照伪装成历史数据。

### 2.4 来源可靠性与冲突处理

当输入能够识别来源类型且时间相关时，优先顺序为：

```text
监管披露或正式财报
    ↓
公司投资者关系材料
    ↓
标准化公司资料
    ↓
其他辅助来源
```

如果不同来源出现冲突：

- 在 `warnings` 中说明冲突；
- 使用保守且仍有证据支持的结论；
- 降低 `confidence`；
- 不选择让公司看起来更强的数据。

数据不存在或无法追踪来源时，使用：

```text
insufficient_evidence
```

### 2.5 统一 LLM 接口

Company Agent 不单独创建 LLM 客户端，而是复用：

```python
from multiple_agent_finance.llm import get_agent_llm

llm = get_agent_llm("company")
```

所有模型配置继续读取项目 `.env` 中的 `MAF_LLM_*` 变量。Company Agent 没有独立 API Key、Base URL 或模型配置。

### 2.6 结构化输出与降级处理

Company Agent 的 LLM 调用顺序为：

```text
with_structured_output(CompanyAnalysis)
    ↓ 不支持或失败
response_format={"type": "json_object"} + 完整 JSON Schema
    ↓ 仍然失败
确定性 status="degraded" Company Result
```

当前 DeepSeek 端点不支持项目优先尝试的 `json_schema` response format，因此会使用同一 LLM 的 `json_object` fallback。

如果 LLM 或数据源失败，Company Agent 仍返回统一 JSON，不会让 Company 分支异常中断，也不会丢失 Technical Result。

### 2.7 Prompt 后期调整

最终 Prompt 使用“结构化单阶段”方式，在一次模型调用中完成：

```text
证据校验 -> 六维分析 -> 置信度校准 -> CompanyAnalysis JSON
```

主要调整包括：

- 强制区分 `as_of_date`、`period_end` 和 `filed_at`；
- 增加 current snapshot 与历史 point-in-time 的边界；
- 增加来源优先级和 conflicting evidence 处理；
- 不允许仅凭市值或品牌推断行业领导地位和护城河；
- `confidence` 只表示证据支持程度，不代表上涨概率或投资胜率；
- 多个核心维度缺少证据时使用 `status="degraded"`；
- 竞争优势最多 5 项；
- 风险因素最多 6 项；
- 不重复长段原始证据；
- 不输出隐藏推理、第二份叙事报告或交易建议；
- 只返回符合 Schema 的 JSON。

## 3. 修改文件位置

Company Agent 功能新增文件为：

```text
src/multiple_agent_finance/agents/company_schema.py
src/multiple_agent_finance/graph/company_technical_parallel.py
tests/test_company_agent.py
```

Company Agent 功能修改文件为：

```text
.gitignore
src/multiple_agent_finance/agents/company.py
src/multiple_agent_finance/graph/state.py
src/multiple_agent_finance/prompts/company.md
src/multiple_agent_finance/tools/company_tools.py
```

本次明确没有修改：

```text
Data Layer
src/multiple_agent_finance/agents/technical.py
src/multiple_agent_finance/tools/technical_tools.py
src/multiple_agent_finance/agents/planner.py
src/multiple_agent_finance/agents/decision.py
src/multiple_agent_finance/agents/reflection.py
```

当前功能分支为：

```text
company-agent
```

最新代码提交为：

```text
4aa01e77a65eacf8aa85607f6871cd71db083b60
refine company analysis prompt
```

## 4. 运行指令

### 4.1 激活项目虚拟环境

```powershell
conda activate multiple_agent_finance
```

确认当前 Python：

```powershell
where.exe python
python -c "import sys; print(sys.executable)"
```

确认 yfinance：

```powershell
python -m pip show yfinance
python -c "import yfinance as yf; print(yf.__version__)"
```

如果提示 `ModuleNotFoundError`，说明当前 Python 环境没有安装项目依赖，而不是 Yahoo 限流。

### 4.2 大模型连接测试

普通配置检查：

```powershell
python scripts/check_llm_connection.py
```

真实线上调用测试：

```powershell
python scripts/check_llm_connection.py --live
```

说明：

- `.env` 中需要配置项目统一的 LLM 参数；
- 不要把真实 API Key 写入代码、测试或报告；
- 日志中只记录 `api_key_configured=true/false`。

### 4.3 当前主程序接入范围

当前交互式主程序只提供：

```text
full
technical-chain
```

Company/Technical 并行图目前是独立图构建器，没有增加新的 CLI mode。这是为了不修改现有 Planner、Decision 和 Reflection 流程。

并行图入口为：

```python
from multiple_agent_finance.graph.company_technical_parallel import (
    build_company_technical_parallel_graph,
)

graph = build_company_technical_parallel_graph()
```

调用 `graph.invoke(state)` 前，需要在 State 中提供标准化 `market_data` 和 `company_data`。如果缺少 `company_data`，Company Agent 会调用 Company Tool fallback。

### 4.4 本地真实数据与在线模型验证

本地验证脚本位于 Company Agent worktree 的忽略目录中：

```text
.runtime_deps/run_live_data_company_parallel.py
```

运行方式：

```powershell
python .runtime_deps/run_live_data_company_parallel.py
```

该脚本只用于本地验证，没有提交到 GitHub。它会使用：

- Yahoo Chart JSON：AAPL 近一年日线；
- Apple 2025 Form 10-K：公司基本面证据；
- 项目现有 DeepSeek LLM 接口；
- Company/Technical 并行图。

执行真实在线测试可能产生 LLM Token 费用。

### 4.5 数据库脚本

项目提供以下 MySQL 辅助脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/init_mysql_database.ps1
powershell -ExecutionPolicy Bypass -File scripts/start_mysql.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop_mysql.ps1
```

数据库初始化和 Company Result 落库已经在前一次隔离 MySQL 8.0 端到端测试中通过。本次 Prompt 调整没有修改数据库结构。

## 5. 测试指令

### 5.1 测试 Prompt 合同

```powershell
python -m pytest -q tests/test_company_agent.py::test_company_prompt_enforces_reliability_depth_and_token_contract
```

该测试重点检查：

- `period_end` 和 `filed_at`；
- point-in-time 与 current snapshot；
- conflicting evidence 与保守结论；
- confidence 的正确含义；
- `status="degraded"`；
- `insufficient_evidence`；
- 竞争优势和风险数量上限；
- JSON-only 输出。

最终测试通过：

```text
tests/test_company_agent.py::test_company_prompt_enforces_reliability_depth_and_token_contract PASSED
1 passed in 1.59s
```

### 5.2 测试 Company Agent

```powershell
python -m pytest -q tests/test_company_agent.py -vv
```

该测试用于验证：

- Company Schema；
- yfinance Company Tool 标准化；
- 预加载 `company_data` 优先级；
- 统一 LLM 接口；
- structured output；
- JSON object fallback；
- degraded fallback；
- Prompt 合同；
- Company/Technical 并行图；
- Company 降级时 Technical Result 仍保留。

最终测试通过：

```text
collected 17 items
tests/test_company_agent.py .................                         [100%]
17 passed in 1.98s
```

### 5.3 运行全部测试

```powershell
python -m pytest -q
```

最终全量测试结果：

```text
................................                                 [100%]
32 passed in 2.25s
```

### 5.4 静态检查

```powershell
python -m ruff check tests/test_company_agent.py
python -m ruff format --check tests/test_company_agent.py
git diff --check
```

最终结果：

```text
Ruff check: All checks passed
Ruff format: 1 file already formatted
git diff --check: 无空白错误
```

如后续继续修改 Company Prompt 或 Company Agent，建议至少重新运行：

```powershell
python -m pytest -q tests/test_company_agent.py -vv
python -m pytest -q
```

## 6. 真实联网运行结果

### 6.1 yfinance 与 Yahoo Chart

原项目 yfinance 调用返回：

```text
YFRateLimitError: Too Many Requests. Rate limited. Try after a while.
```

同一环境直接请求 Yahoo Chart JSON 返回 HTTP 200。因此本地验证临时使用 Yahoo Chart 获取 OHLCV，并复用项目 `history_to_records()` 生成标准 `market_data`。

该临时适配没有修改 Data Layer，也没有提交到 GitHub。

### 6.2 AAPL 并行分析结果

真实数据与在线 DeepSeek 运行结果为：

```text
ticker=AAPL
market_rows=251
market_first_date=2025-07-17
market_last_date=2026-07-16
company_status=success
company_confidence=0.9
technical_trend=bullish
volume_signal=neutral
macd_signal=bullish
rsi_signal=overbought
latest_price=333.260009765625
latest_trading_date=2026-07-16
```

Company Result 覆盖商业模式、行业地位、竞争优势、财务健康、成长性和风险因素六个维度。

说明：该在线结果生成于本轮最终 Prompt 调整之前，用于证明真实数据、在线 LLM、Company Agent 与 Technical Agent 并行链路能够运行。本轮最终 Prompt 通过自动化测试验证，但没有再次产生付费在线调用。

### 6.3 数据库验证结果

前一次隔离 MySQL 8.0 端到端验证结果为：

- 初始化 16 张业务表；
- AAPL、MSFT、NVDA 种子股票存在；
- `analysis_runs` 状态为 completed；
- Company Profile 成功落库 1 条；
- Company Agent 输出成功落库 1 条。

最近一次 Yahoo/SEC 联网验证没有重复写库，数据库持久化由前一次独立验证覆盖。

## 7. Token 说明与已知限制

上次在线响应没有保存供应商返回的 `prompt_tokens`、`completion_tokens` 和 `total_tokens`，因此以下为工程估算，不是账单数据。

使用上次 AAPL 证据重建最终 Prompt 消息：

| 项目 | 字符数 |
|---|---:|
| Company System Prompt | 4,060 |
| AAPL HumanMessage | 2,889 |
| 结构化输入合计 | 6,949 |
| fallback Schema 消息 | 6,747 |
| fallback 输入合计 | 13,696 |
| 上次 Company JSON 输出 | 5,514 |

粗略估算：

- 原生结构化输出：约 3,100–4,200 tokens；
- 当前 DeepSeek JSON fallback：约 4,800–6,400 tokens；
- 如果被拒绝的 structured request 也计费：可能约 6,500–8,700 tokens。

实际费用以供应商 usage 为准。

当前已知限制：

- yfinance/Yahoo 没有生产 SLA，可能出现 401、429 或 Cookie/Crumb 问题；
- Yahoo Chart 日线不是交易所级实时行情；
- Yahoo Chart 不提供完整 PE/PB 和公司基本面；
- 当前 DeepSeek fallback 会额外发送完整 JSON Schema；
- Company/Technical 并行图尚未增加主程序 CLI mode；
- Decision/Reflection 的后续正式接入需要单独设计。


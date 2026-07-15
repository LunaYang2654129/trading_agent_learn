# Company Agent Parallel Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a structured, LLM-backed Company Agent and an isolated Company–Technical parallel graph without changing the Data Layer, Technical Agent, Planner Agent, Decision Agent, Reflection Agent, or existing graph builders.

**Architecture:** Company Agent prefers preloaded `state.company_data`, falls back to the existing Company Tool, loads `prompts/company.md`, and calls the shared `get_agent_llm("company")`. A Pydantic schema stabilizes the six-dimension JSON result, while structured-output, plain-JSON, and deterministic degraded paths prevent Company failures from interrupting Technical analysis. A new graph fans out from the unchanged Planner to unchanged Technical and the new Company Agent, then joins both outputs into `parallel_analysis_result`.

**Tech Stack:** Python 3.11+, LangGraph, LangChain `ChatOpenAI`, Pydantic v2, pytest, yfinance.

## Global Constraints

- Do not modify the Data Layer.
- Do not modify `agents/technical.py`, `tools/technical_tools.py`, `agents/planner.py`, `agents/decision.py`, `agents/reflection.py`, `graph/builder.py`, or `graph/technical_chain.py`.
- Use `get_agent_llm("company")`; never construct a second LLM client or persist credentials.
- Preserve `company_profile` and its legacy root fields for existing Decision/storage compatibility.
- Every Company execution returns valid JSON, including LLM/tool failure paths.
- Do not output real trading orders or buy/sell recommendations.
- Keep the existing `.env.example` and `.runtime_deps/` worktree changes out of task commits.

---

### Task 1: Company Result Schema

**Files:**
- Create: `src/multiple_agent_finance/agents/company_schema.py`
- Test: `tests/test_company_agent.py`

**Interfaces:**
- Produces: `CompanyAnalysis.model_validate(value)` and `CompanyAnalysis.model_dump(mode="json")`.
- Produces nested models: `BusinessModelAnalysis`, `IndustryPositionAnalysis`, `CompetitiveAdvantage`, `FinancialHealthAnalysis`, `GrowthAnalysis`, and `RiskFactor`.
- Later tasks rely on root compatibility fields `business_summary`, `sector`, `industry`, `main_products`, `competitive_position`, and `key_risks`.

- [ ] **Step 1: Write failing schema tests**

Add tests that construct a complete payload, validate it, serialize it with `json.dumps`, and reject invalid `confidence`, `durability`, and `severity` values:

```python
def test_company_analysis_schema_serializes_six_dimensions():
    analysis = CompanyAnalysis.model_validate(_valid_company_payload())
    payload = analysis.model_dump(mode="json")
    assert payload["business_model"]["summary"] == "Consumer hardware and services ecosystem."
    assert payload["industry_position"]["position"] == "Global category leader."
    assert payload["competitive_advantages"][0]["durability"] == "high"
    assert payload["financial_health"]["assessment"] == "healthy"
    assert payload["growth"]["assessment"] == "moderate"
    assert payload["risk_factors"][0]["severity"] == "medium"
    assert payload["competitive_position"]
    assert payload["key_risks"]
    json.dumps(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("confidence",), 1.5),
        (("competitive_advantages", 0, "durability"), "permanent"),
        (("risk_factors", 0, "severity"), "critical"),
    ],
)
def test_company_analysis_schema_rejects_invalid_control_values(path, value):
    payload = _valid_company_payload()
    _set_nested(payload, path, value)
    with pytest.raises(ValidationError):
        CompanyAnalysis.model_validate(payload)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: collection fails with `ModuleNotFoundError: multiple_agent_finance.agents.company_schema`.

- [ ] **Step 3: Implement the schema**

Create strict Pydantic models with these exact fields:

```python
class BusinessModelAnalysis(BaseModel):
    summary: str
    products_services: list[str] = Field(default_factory=list)
    revenue_drivers: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class IndustryPositionAnalysis(BaseModel):
    sector: str
    industry: str
    position: str
    market_position_evidence: list[str] = Field(default_factory=list)


class CompetitiveAdvantage(BaseModel):
    advantage: str
    durability: Literal["low", "medium", "high", "unknown"]
    evidence: str


class FinancialHealthAnalysis(BaseModel):
    assessment: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class GrowthAnalysis(BaseModel):
    assessment: str
    growth_drivers: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class RiskFactor(BaseModel):
    risk: str
    severity: Literal["low", "medium", "high", "unknown"]
    evidence: str


class CompanyAnalysis(BaseModel):
    ticker: str
    as_of_date: str | None = None
    company_name: str
    status: Literal["success", "degraded"]
    business_model: BusinessModelAnalysis
    industry_position: IndustryPositionAnalysis
    competitive_advantages: list[CompetitiveAdvantage] = Field(default_factory=list)
    financial_health: FinancialHealthAnalysis
    growth: GrowthAnalysis
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    business_summary: str
    sector: str
    industry: str
    main_products: list[str] = Field(default_factory=list)
    competitive_position: str
    key_risks: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run schema tests and verify GREEN**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: schema tests pass.

- [ ] **Step 5: Commit the schema slice**

```powershell
git add -- src/multiple_agent_finance/agents/company_schema.py tests/test_company_agent.py
git commit -m "feat: define company analysis schema"
```

### Task 2: Company Evidence Tool

**Files:**
- Modify: `src/multiple_agent_finance/tools/company_tools.py`
- Test: `tests/test_company_agent.py`

**Interfaces:**
- Produces: `get_company_profile(ticker: str, as_of_date: str | None = None) -> dict[str, Any]`.
- Output keys: `ticker`, `as_of_date`, `company_name`, `business_summary`, `sector`, `industry`, `main_products`, `website`, `market_cap`, `competitive_evidence`, `financial_evidence`, `growth_evidence`, `warnings`, and `sources`.
- Consumed by `company_agent_node` when `state.company_data` is absent.

- [ ] **Step 1: Write failing tool tests**

Monkeypatch `sys.modules["yfinance"]` with a fake module and assert normalization:

```python
def test_get_company_profile_returns_normalized_company_evidence(monkeypatch):
    _install_fake_yfinance(monkeypatch, _raw_company_info())
    result = get_company_profile("aapl", as_of_date="2026-07-15")
    assert result["ticker"] == "AAPL"
    assert result["as_of_date"] == "2026-07-15"
    assert result["company_name"] == "Apple Inc."
    assert result["financial_evidence"]["total_cash"] == 100.0
    assert result["growth_evidence"]["revenue_growth"] == 0.08
    assert result["sources"] == [{"type": "company_profile", "name": "yfinance"}]


def test_get_company_profile_returns_stable_fallback(monkeypatch):
    _install_failing_yfinance(monkeypatch, RuntimeError("offline"))
    result = get_company_profile("aapl", as_of_date="2026-07-15")
    assert result["ticker"] == "AAPL"
    assert result["financial_evidence"]["total_cash"] is None
    assert result["growth_evidence"]["revenue_growth"] is None
    assert result["warnings"] == ["公司资料获取失败: offline"]
```

- [ ] **Step 2: Run tool tests and verify RED**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: failure because the old function does not accept `as_of_date` or return evidence groups.

- [ ] **Step 3: Implement normalized evidence**

Keep `_extract_products`, add a local `_safe_float`, and map these yfinance fields:

```python
financial_evidence = {
    "total_cash": _safe_float(info.get("totalCash")),
    "total_debt": _safe_float(info.get("totalDebt")),
    "debt_to_equity": _safe_float(info.get("debtToEquity")),
    "current_ratio": _safe_float(info.get("currentRatio")),
    "profit_margins": _safe_float(info.get("profitMargins")),
    "operating_cashflow": _safe_float(info.get("operatingCashflow")),
    "free_cashflow": _safe_float(info.get("freeCashflow")),
}
growth_evidence = {
    "revenue_growth": _safe_float(info.get("revenueGrowth")),
    "earnings_growth": _safe_float(info.get("earningsGrowth")),
    "earnings_quarterly_growth": _safe_float(info.get("earningsQuarterlyGrowth")),
}
```

The fallback must return the same keys and `None` for unavailable numeric evidence.

- [ ] **Step 4: Run tool tests and verify GREEN**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: schema and tool tests pass.

- [ ] **Step 5: Commit the tool slice**

```powershell
git add -- src/multiple_agent_finance/tools/company_tools.py tests/test_company_agent.py
git commit -m "feat: normalize company evidence"
```

### Task 3: LLM-backed Company Agent and Prompt

**Files:**
- Modify: `src/multiple_agent_finance/agents/company.py`
- Modify: `src/multiple_agent_finance/prompts/company.md`
- Test: `tests/test_company_agent.py`

**Interfaces:**
- Preserves: `company_agent_node(state: StockAnalysisState) -> dict[str, Any]`.
- Adds internal helpers `_load_prompt`, `_build_messages`, `_extract_message_content`, `_parse_json_object`, `_invoke_company_model`, and `_build_degraded_analysis`.
- Consumes `state.company_data`, falling back to `get_company_profile`.
- Produces `company_profile`, one `shared_memory_refs` entry, and one `audit_log` entry.

- [ ] **Step 1: Write failing agent tests**

Use fake structured/plain LLM objects and monkeypatch `get_agent_llm`:

```python
def test_company_agent_uses_shared_llm_and_preloaded_data(monkeypatch):
    captured = {}
    llm = _structured_llm(captured, _valid_company_payload())
    monkeypatch.setattr(company_module, "get_agent_llm", lambda name: captured.setdefault("name", name) or llm)
    monkeypatch.setattr(company_module, "get_company_profile", _unexpected_tool_call)
    result = company_module.company_agent_node(_company_state(company_data=_company_evidence()))
    assert captured["name"] == "company"
    assert result["company_profile"]["status"] == "success"
    assert result["company_profile"]["ticker"] == "AAPL"
    assert "2026-07-15" in str(captured["messages"])
    assert "Evaluate durable company quality" in str(captured["messages"])


def test_company_agent_falls_back_to_plain_json(monkeypatch):
    llm = _plain_json_fallback_llm(_valid_company_payload())
    monkeypatch.setattr(company_module, "get_agent_llm", lambda name: llm)
    result = company_module.company_agent_node(_company_state(company_data=_company_evidence()))
    assert result["company_profile"]["status"] == "success"
    llm.invoke.assert_called_once()


def test_company_agent_returns_degraded_json_when_llm_fails(monkeypatch):
    monkeypatch.setattr(company_module, "get_agent_llm", lambda name: _failing_llm())
    result = company_module.company_agent_node(_company_state(company_data=_company_evidence()))
    profile = result["company_profile"]
    assert profile["status"] == "degraded"
    assert profile["confidence"] <= 0.3
    assert set(profile) >= _required_company_keys()
    assert result["shared_memory_refs"] == [{"agent": "company_agent", "key": "company_profile"}]
    assert result["audit_log"][0]["agent"] == "company_agent"
```

Also add tests for tool fallback, fenced JSON parsing, empty content, and legacy aliases.

- [ ] **Step 2: Run agent tests and verify RED**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: failures because Company Agent does not call the LLM or load the prompt.

- [ ] **Step 3: Implement Prompt instructions**

Replace `prompts/company.md` with explicit instructions covering the six dimensions, evidence-only reasoning, `as_of_date`, JSON-only output, `insufficient_evidence`, and prohibition of transaction recommendations.

- [ ] **Step 4: Implement the structured/plain/degraded call path**

Use the existing LLM factory:

```python
llm = get_agent_llm("company")
try:
    structured_llm = llm.with_structured_output(CompanyAnalysis)
    raw = structured_llm.invoke(messages)
    return CompanyAnalysis.model_validate(raw).model_dump(mode="json")
except Exception as structured_exc:
    try:
        response = llm.invoke(messages)
        raw_json = _parse_json_object(_extract_message_content(response))
        return CompanyAnalysis.model_validate(raw_json).model_dump(mode="json")
    except Exception as plain_exc:
        return _build_degraded_analysis(evidence, structured_exc, plain_exc)
```

Load `company.md` with an explicit UTF-8 read. The deterministic fallback must preserve company identity and evidence aliases while using `insufficient_evidence` for unsupported conclusions.

- [ ] **Step 5: Run Company Agent tests and verify GREEN**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: all schema, tool, and agent tests pass without network access.

- [ ] **Step 6: Commit the agent slice**

```powershell
git add -- src/multiple_agent_finance/agents/company.py src/multiple_agent_finance/prompts/company.md tests/test_company_agent.py
git commit -m "feat: add llm-backed company agent"
```

### Task 4: Company–Technical Parallel Graph

**Files:**
- Modify: `src/multiple_agent_finance/graph/state.py`
- Create: `src/multiple_agent_finance/graph/company_technical_parallel.py`
- Test: `tests/test_company_agent.py`

**Interfaces:**
- Adds state fields `company_data: dict[str, Any]` and `parallel_analysis_result: dict[str, Any]`.
- Produces: `build_company_technical_parallel_graph()`.
- Result collector consumes `technical_indicators` and `company_profile`, and produces `parallel_analysis_result`.

- [ ] **Step 1: Write failing parallel graph tests**

```python
def test_company_technical_parallel_graph_has_expected_nodes():
    graph = build_company_technical_parallel_graph()
    assert set(graph.get_graph().nodes) == {
        "__start__",
        "planner",
        "technical_agent",
        "company_agent",
        "result_collector",
        "__end__",
    }


def test_company_technical_parallel_graph_collects_both_results(monkeypatch):
    _install_graph_fakes(monkeypatch)
    graph = parallel_module.build_company_technical_parallel_graph()
    result = graph.invoke(_parallel_state())
    joined = result["parallel_analysis_result"]
    assert joined["technical_result"] == {"trend": "bullish", "warnings": []}
    assert joined["company_result"]["status"] == "success"
    assert joined["warnings"] == []
```

Add a test whose fake Company node returns `status="degraded"` and warnings while Technical remains present.

- [ ] **Step 2: Run graph tests and verify RED**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: import failure because `graph.company_technical_parallel` does not exist.

- [ ] **Step 3: Extend State and implement the graph**

Build the graph without modifying existing builders:

```python
workflow = StateGraph(StockAnalysisState)
workflow.add_node("planner", planner_agent_node)
workflow.add_node("technical_agent", technical_agent_node)
workflow.add_node("company_agent", company_agent_node)
workflow.add_node("result_collector", collect_parallel_results)
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "technical_agent")
workflow.add_edge("planner", "company_agent")
workflow.add_edge(["technical_agent", "company_agent"], "result_collector")
workflow.add_edge("result_collector", END)
return workflow.compile()
```

`collect_parallel_results` must preserve each specialist payload and concatenate their warning lists without mutation.

- [ ] **Step 4: Run parallel graph tests and verify GREEN**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: all Company Agent tests pass.

- [ ] **Step 5: Commit the graph slice**

```powershell
git add -- src/multiple_agent_finance/graph/state.py src/multiple_agent_finance/graph/company_technical_parallel.py tests/test_company_agent.py
git commit -m "feat: add company technical parallel graph"
```

### Task 5: Regression Verification and Handoff

**Files:**
- Verify only; no planned production changes.

**Interfaces:**
- Confirms the new graph and Company Agent do not alter existing graph contracts.

- [ ] **Step 1: Run the standalone Company suite**

Run: `python -m pytest tests/test_company_agent.py -q`

Expected: all tests pass.

- [ ] **Step 2: Run Technical regression tests**

Run: `python -m pytest tests/test_technical_agent.py tests/test_scaffold_imports.py -q`

Expected: all existing Technical and graph scaffold tests pass unchanged.

- [ ] **Step 3: Run the complete suite**

Run: `python -m pytest -q`

Expected: zero failures.

- [ ] **Step 4: Check formatting and scope**

Run:

```powershell
python -m ruff check src/multiple_agent_finance/agents/company.py src/multiple_agent_finance/agents/company_schema.py src/multiple_agent_finance/tools/company_tools.py src/multiple_agent_finance/graph/company_technical_parallel.py tests/test_company_agent.py
git diff --check
git status --short
```

Expected: no Ruff errors, no whitespace errors, and only intentional task files plus the user's pre-existing `.env.example`/`.runtime_deps/` changes.

- [ ] **Step 5: Prepare final report**

Report four required sections using actual evidence from the preceding commands:

- Added files.
- Modified files.
- Runtime call flow.
- Test commands and exact pass counts.

Also state that Reflection Agent was intentionally unchanged because this isolated parallel chain stops before Decision/Reflection, avoiding false Financial/News missing-item retries.

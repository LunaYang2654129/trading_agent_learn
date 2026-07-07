# LangGraph 股票多智能体框架目录结构

本目录结构按图片中的框架创建：

```text
用户输入
  -> Planner Agent
  -> Parallel Multi-Agent Layer
       -> Tool Layer
       -> Company Agent
       -> Financial Agent
       -> News Agent
       -> Risk Agent
  -> Decision Agent
  -> Reflection Agent
  -> Confidence >= Threshold?
       -> 是: Final Report -> 输出
       -> 否: Retry -> Planner Agent
```

## 代码目录

| 路径 | 对应框架模块 |
| --- | --- |
| `src/multiple_agent_finance/main.py` | 用户输入 / demo 入口 |
| `src/multiple_agent_finance/graph/` | LangGraph State、Edge、Route、Graph Builder |
| `src/multiple_agent_finance/agents/planner.py` | Planner Agent |
| `src/multiple_agent_finance/agents/company.py` | Company Agent |
| `src/multiple_agent_finance/agents/financial.py` | Financial Agent |
| `src/multiple_agent_finance/agents/news.py` | News Agent |
| `src/multiple_agent_finance/agents/risk.py` | Risk Agent |
| `src/multiple_agent_finance/agents/decision.py` | Decision Agent |
| `src/multiple_agent_finance/agents/reflection.py` | Reflection Agent |
| `src/multiple_agent_finance/tools/` | Tool Layer |
| `src/multiple_agent_finance/memory/` | Shared Memory |
| `src/multiple_agent_finance/knowledge_base/` | Knowledge Base |
| `src/multiple_agent_finance/external_data/` | 外部数据源 |
| `src/multiple_agent_finance/reports/` | 最终报告生成 |
| `src/multiple_agent_finance/prompts/` | 各 Agent prompt 模板 |

## 数据与运行目录

| 路径 | 用途 |
| --- | --- |
| `data/external/` | 外部数据落地 |
| `data/knowledge_base/` | 知识库文件 |
| `data/shared_memory/` | 共享记忆持久化 |
| `data/raw/` | 原始数据 |
| `data/processed/` | 处理后数据 |
| `checkpoints/` | LangGraph checkpoint |
| `outputs/reports/` | 最终报告 |
| `outputs/logs/` | 运行日志 |

## 运行示例

```powershell
conda activate multiple_agent_finance
$env:PYTHONPATH="src"
python -m multiple_agent_finance.main
```

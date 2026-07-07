# multiple_agent_finance 环境说明

已创建 conda 环境：

```powershell
conda activate multiple_agent_finance
```

Python 版本：

```text
Python 3.11.15
```

## 安装文件

本工作区新增两个环境文件：

- `requirements_multiple_agent_finance.txt`: pip 依赖清单。
- `environment_multiple_agent_finance.yml`: conda + pip 重建环境清单。

## 重建方式

如果需要从零重建：

```powershell
conda env create -f environment_multiple_agent_finance.yml
```

如果环境已经存在，只同步依赖：

```powershell
conda activate multiple_agent_finance
conda install -c conda-forge swig ta-lib -y
python -m pip install --default-timeout 120 --retries 10 -r requirements_multiple_agent_finance.txt
```

## 已验证能力

已验证以下核心依赖可正常导入：

- LangGraph / LangChain / OpenAI
- pandas / numpy / scipy / scikit-learn
- yfinance / stockstats / pandas-market-calendars
- pydantic / sqlalchemy / python-dotenv
- matplotlib / plotly / seaborn / streamlit
- python-docx / markdown
- ta-lib
- torch / stable-baselines3 / gymnasium
- bt / alpaca-py / alpaca-trade-api / ccxt

`pip check` 结果：

```text
No broken requirements found.
```

## 说明

第一版项目以会议纪要中的 7 节点 LangGraph 股票分析系统为目标，因此环境优先保证 LangGraph、多 Agent、数据分析、行情/财务/新闻处理和报告生成可用。

FinRL/DRL/回测相关依赖也已安装到可用范围，作为二期扩展基础。

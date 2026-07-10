# Conda 虚拟环境 multiple_agent_finance 创建教程

本文档说明如何从零创建并验证本项目使用的 conda 虚拟环境：

```text
multiple_agent_finance
```

适用项目路径：

```text
C:\Users\10136\Desktop\trading_agent_learn
```

## 1. 前置条件

需要先安装 Anaconda 或 Miniconda。

验证 conda 是否可用：

```powershell
conda --version
```

建议使用 PowerShell 或 Anaconda Prompt 执行后续命令。

## 2. 进入项目目录

```powershell
cd C:\Users\10136\Desktop\trading_agent_learn
```

确认项目根目录下存在以下文件：

```text
environment_multiple_agent_finance.yml
requirements.txt
pyproject.toml
```

## 3. 分步创建环境

先只创建基础环境，指定环境名和 Python 版本：

```powershell
conda create -n multiple_agent_finance python=3.11 pip -y
```

参数说明：

- `-n multiple_agent_finance`：创建名为 `multiple_agent_finance` 的环境。
- `python=3.11`：项目推荐 Python 版本。
- `pip`：后续用于安装 Python 包。
- `-y`：自动确认创建过程。

## 4. 激活环境

```powershell
conda activate multiple_agent_finance
```

激活成功后，命令行前缀应显示：

```text
(multiple_agent_finance)
```

检查 Python 路径：

```powershell
python -c "import sys; print(sys.executable)"
```

期望看到类似：

```text
C:\Users\10136\.conda\envs\multiple_agent_finance\python.exe
```

## 5. 安装 conda 原生依赖

安装需要原生库支持的依赖：

```powershell
conda install -c conda-forge swig ta-lib -y
```

说明：

- `swig`：部分量化/金融依赖可能需要。
- `ta-lib`：技术指标相关原生库，推荐由 conda-forge 安装，避免 Windows 下 pip 编译失败。

## 6. 升级 pip

```powershell
python -m pip install --upgrade pip
```

## 7. 安装 Python 依赖

从项目的总依赖文件安装：

```powershell
python -m pip install -r requirements.txt
```

如果网络较慢，可以换用国内镜像：

```powershell
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 8. 安装项目为可编辑模式

建议在环境中安装当前项目：

```powershell
python -m pip install -e .
```

这样可以直接运行：

```powershell
python -m multiple_agent_finance.main --help
```

## 9. 如果环境已存在，只同步依赖

如果已经创建过环境，不需要重新创建，可以执行：

```powershell
conda activate multiple_agent_finance
conda install -c conda-forge swig ta-lib -y
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 10. environment 文件与分步命令对应关系

项目保留了 `environment_multiple_agent_finance.yml`，但本教程不使用 `-f` 一次性创建。该文件中的配置可以拆成下面这些命令理解和执行：

```powershell
conda create -n multiple_agent_finance python=3.11 pip -y
conda activate multiple_agent_finance
conda install -c conda-forge swig ta-lib -y
python -m pip install -r requirements.txt
```

拆分后的好处是：创建环境、安装原生依赖、安装 Python 依赖三个阶段可以分别排错。

## 11. 配置 .env

复制示例文件：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`。

LLM 配置示例：

```env
MAF_LLM_PROVIDER=volcengine_ark
MAF_LLM_MODEL=deepseek-v4-flash
MAF_LLM_ENDPOINT_ID=你的火山方舟接入点ID
MAF_LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
MAF_LLM_API_KEY=你的火山引擎API_KEY
MAF_LLM_TEMPERATURE=0.2
MAF_LLM_TIMEOUT=60
```

MySQL 配置示例：

```env
MAF_MYSQL_HOST=127.0.0.1
MAF_MYSQL_PORT=3306
MAF_MYSQL_USER=maf_app
MAF_MYSQL_PASSWORD=maf_password_change_me
MAF_MYSQL_DATABASE=multiple_agent_finance
```

安全要求：

- `.env` 只保存在本地。
- 不要提交 `.env` 到 GitHub。
- 不要把真实 API key 写入代码或文档。

## 12. 验证核心依赖

运行：

```powershell
python -c "import langgraph, pandas, yfinance, sqlalchemy; print('core imports ok')"
```

验证 LangChain OpenAI 兼容客户端：

```powershell
python -c "from langchain_openai import ChatOpenAI; print('langchain_openai ok')"
```

验证技术指标依赖：

```powershell
python -c "import talib; print('ta-lib ok')"
```

如果 `talib` 导入失败，优先重新安装 conda-forge 版本：

```powershell
conda install -c conda-forge ta-lib -y
```

## 13. 检测火山引擎 LLM 配置

离线检测：

```powershell
python scripts/check_llm_connection.py
```

成功时应看到：

```json
{
  "status": "ok",
  "expected_model": "deepseek-v4-flash"
}
```

真实连通性检测：

```powershell
python scripts/check_llm_connection.py --live
```

如果返回：

```text
InvalidEndpointOrModel.NotFound
```

说明需要在 `.env` 中配置火山方舟实际接入点 ID：

```env
MAF_LLM_ENDPOINT_ID=ep-xxxxxxxxxxxxxxxx
```

## 14. 运行项目测试

```powershell
pytest -q
```

当前期望：

```text
15 passed
```

如果测试数量因后续开发变化，以实际项目测试为准。

## 15. 编译检查

```powershell
python -m compileall -q scripts src tests
```

无输出通常表示通过。

## 16. 运行单链路技术预测

当前本周最小 Graph 为：

```text
planner -> technical_agent -> decision_agent -> reflection_agent -> final_report
```

使用预加载 CSV 数据运行：

```powershell
python -m multiple_agent_finance.main `
  --mode technical-chain `
  --ticker 002230.SZ `
  --date 2026-04-15 `
  --market-period 2026-03-16_to_2026-04-15 `
  --market-data-csv data/raw/market/002230_SZ_20260316_20260415.csv
```

报告输出目录：

```text
outputs/reports/
```

## 17. 常见问题

### 17.1 conda 创建或安装太慢

建议使用国内镜像或确保网络稳定。分步安装时可以先完成 conda 依赖，再安装 pip 依赖：

```powershell
conda create -n multiple_agent_finance python=3.11 pip -y
conda activate multiple_agent_finance
conda install -c conda-forge swig ta-lib -y
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 17.2 `ModuleNotFoundError`

确认当前环境是否正确：

```powershell
conda info --envs
python -c "import sys; print(sys.executable)"
```

如果不是 `multiple_agent_finance`，重新激活：

```powershell
conda activate multiple_agent_finance
```

### 17.3 `langchain_openai` 缺失

安装依赖：

```powershell
python -m pip install langchain-openai
```

或重新安装完整依赖：

```powershell
python -m pip install -r requirements.txt
```

### 17.4 PowerShell 显示中文乱码

文件通常仍是 UTF-8。可用 Python 验证：

```powershell
python -c "from pathlib import Path; print(Path('docs/conda_multiple_agent_finance_tutorial.md').read_text(encoding='utf-8')[:200])"
```

### 17.5 需要删除并重建环境

```powershell
conda deactivate
conda env remove -n multiple_agent_finance
conda create -n multiple_agent_finance python=3.11 pip -y
conda activate multiple_agent_finance
conda install -c conda-forge swig ta-lib -y
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 18. 推荐日常命令

进入项目：

```powershell
cd C:\Users\10136\Desktop\trading_agent_learn
```

激活环境：

```powershell
conda activate multiple_agent_finance
```

检测 LLM：

```powershell
python scripts/check_llm_connection.py
```

跑测试：

```powershell
pytest -q
```

跑单链路：

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker 002230.SZ --date 2026-04-15 --market-data-csv data/raw/market/002230_SZ_20260316_20260415.csv
```

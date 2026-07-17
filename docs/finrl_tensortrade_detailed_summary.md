# FinRL 系列论文与 TensorTrade 代码详细总结

本文基于工作区已有论文文本和本地 TensorTrade 代码整理，重点补充：使用的方法、强化学习交易环境设置、状态/动作/奖励设计、实验设置、不足之处，以及对当前项目的可落地建议。

## 1. 金融强化学习交易的统一问题定义

股票或数字资产交易可以被建模成 MDP 或近似 POMDP：

- 状态 `s_t`: 当前账户、持仓、市场行情、技术指标、风险指标、新闻/情绪/基本面等。
- 动作 `a_t`: 买入、卖出、持有、调仓比例、目标权重、订单类型、止损止盈等。
- 奖励 `r_t`: 策略在一步或一段时间内获得的收益，通常需要扣除交易成本、滑点和风险惩罚。
- 状态转移: 由市场下一时刻价格、成交量、订单执行结果和账户更新共同决定。
- 目标: 最大化长期累计折扣奖励，但真实目标通常是最大化风险调整后的净收益，而不是单纯总收益。

金融 RL 和游戏 RL 最大不同在于：市场信号低、噪声高、非平稳、不可重复试错，且每次交易都要付出手续费、滑点和市场冲击。因此，交易 RL 的关键不是只训练一个 PPO/DDPG 模型，而是把数据、环境、成本、约束、回测和执行统一起来。

## 2. FinRL Library 论文详细总结

### 2.1 使用的方法

FinRL 的核心方法是把股票交易封装成 OpenAI Gym 风格的强化学习环境，并提供可直接调用的深度强化学习算法。论文中主要使用和支持以下算法：

- DQN: 离散动作价值函数方法，适合买/卖/持有这类离散动作。
- DDPG: 连续动作 actor-critic 方法，适合输出连续持仓比例或买卖数量。
- TD3: DDPG 的改进，使用双 Q 网络和延迟策略更新，降低过估计。
- PPO: 稳定的 on-policy 策略梯度方法，适合教学、基线和中等复杂度环境。
- SAC: 最大熵 actor-critic 方法，强调探索，适合连续动作空间。
- A2C: 同步 advantage actor-critic，结构简单，训练稳定性较好。
- Ensemble: 在不同窗口中选择表现较好的 agent 组合使用。

FinRL 的主要贡献不是提出新算法，而是提供一个可复现的交易实验流水线：数据下载、特征工程、环境构建、模型训练、验证调参、回测分析。

### 2.2 环境设置

FinRL 把交易环境分成三层：

1. Environment layer: 市场环境，负责接收动作、更新持仓和现金、计算奖励。
2. Agent layer: 强化学习算法，负责学习策略。
3. Application layer: 单股票交易、多股票交易、组合配置等任务。

环境使用历史行情模拟交易。论文提到支持多市场和多频率数据，包括 NASDAQ-100、DJIA、S&P 500、HSI、SSE 50、CSI 300 等，可扩展到日线、小时线、分钟线。

典型环境变量包括：

- 初始现金: 如 100,000 或 1,000,000。
- 股票池: 单标的或多标的。
- 时间步: 每日、每小时或分钟。
- 交易成本: 固定费用或按成交额比例。
- 流动性约束: bid-ask spread、成交量约束等。
- 风险约束: turbulence index 超过阈值时停止买入并逐步卖出。
- 是否允许卖空/融资: 论文环境中主要强调非负现金、交易成本和风险厌恶。

### 2.3 状态空间设置

FinRL 的状态空间通常包含：

- `b_t`: 账户现金余额。
- `h_t`: 当前每只股票持仓数量。
- `p_t`: 当前收盘价。
- `o_t, h_t, l_t`: 开盘价、最高价、最低价。
- `v_t`: 成交量。
- 技术指标: MACD、RSI 等。
- 风险指标: turbulence index。

多股票环境中，状态会把每只股票的价格、持仓和指标拼接起来。例如，如果有 30 只股票，每只股票包含价格、MACD、RSI、CCI、ADX 等，状态维度会快速膨胀。这也是金融 RL 容易过拟合的原因之一。

### 2.4 动作空间设置

FinRL 中常见动作有两种形式：

1. 离散动作:
   - `-1`: 卖出。
   - `0`: 持有。
   - `1`: 买入。

2. 连续或整数动作:
   - `a_i in [-k, k]`: 对第 `i` 只股票买入或卖出若干股。
   - 连续动作可映射为交易股数或目标仓位。

多股票场景下，动作是一个向量。例如 `a_t = [a_1, a_2, ..., a_n]`，每个元素表示对应股票的买卖数量或仓位变化。这样做表达能力强，但动作维度高，训练难度和过拟合风险也更高。

### 2.5 奖励函数设置

FinRL 论文列出几类常见奖励。

组合价值变化：

```text
r_t = V_t - V_{t-1}
```

其中 `V_t` 是当前组合净值。这是最直接的奖励，和赚钱目标一致。

优点是简单直接，能反映真实账户净值变化。缺点是受账户规模影响，数值不稳定；如果不扣交易成本，模型会学到高频换手；也不直接惩罚波动和回撤。

组合对数收益：

```text
r_t = log(V_t / V_{t-1})
```

优点是尺度更稳定，多期收益可加，更适合不同初始资金规模的比较。缺点是仍需显式加入成本和风险项。

Sharpe Ratio：

```text
Sharpe = mean(R_t) / std(R_t)
```

Sharpe 关注风险调整收益，适合作为评估指标，但不适合作为单步训练奖励，因为它需要一段收益序列。窗口太短会噪声大，窗口太长会奖励延迟，也可能被 reward hacking。

更实用的自定义奖励：

```text
r_t = log(V_t / V_{t-1}) - cost_t - risk_penalty_t
```

交易成本可以包括手续费、滑点和 bid-ask spread；风险惩罚可以包括波动率、回撤、turbulence 或 VIX。

### 2.6 实验设置与结果

单股票实验：

- 标的: SPY、QQQ、GOOGL、AMZN、AAPL、MSFT。
- 算法: PPO。
- 时间: 2019-01-01 到 2020-09-23。
- 指标: final value、annualized return、annualized std、Sharpe ratio、max drawdown。
- 结果: 多数标的 Sharpe 高于 S&P 500，但 COVID-19 期间最大回撤较大。

多股票/组合实验：

- 标的: DJIA 成分股。
- 算法: TD3、DDPG。
- 基线: DJIA、最小方差组合。
- 结果: TD3 和 DDPG 的 Sharpe 和回撤指标优于传统基线。

### 2.7 不足之处

- 回测环境仍然简化，成交假设和真实市场有差距。
- turbulence index 计算有延迟，不适合高频或实时交易。
- 交易成本建模较粗，未充分模拟市场冲击、部分成交和订单簿。
- 对幸存者偏差、数据泄漏、复权处理、指数历史成分变化的强调不够。
- 论文结果偏教学展示，不等于可实盘盈利。
- 状态维度较大时，DRL 容易记忆历史噪声。

## 3. FinRL-Meta 论文详细总结

### 3.1 使用的方法

FinRL-Meta 的核心方法是 data-centric AI + DataOps/RLOps。它不再只关注“训练什么模型”，而是关注“如何持续构造高质量动态市场环境”。

完整流程：

1. Task planning: 定义股票交易、组合配置、加密货币交易、高频交易等任务。
2. Data accessing: 从多个数据源获取行情、基本面、新闻、情绪等数据。
3. Data cleaning: 去重、补缺、异常处理、对齐交易日历。
4. Feature engineering: 构造技术指标、基本面因子、情绪特征。
5. Environment building: 封装为 Gym 风格环境。
6. Training-testing-trading: 训练、验证、回测、paper/live trading。
7. Monitoring: 监控收益、风险、交易行为和环境表现。

### 3.2 环境设置

FinRL-Meta 的环境层仍采用 Gym 接口：

- `reset()`: 重置到账户和市场初始状态。
- `step(action)`: 执行动作，更新账户、持仓和市场状态。
- `reward()`: 根据新的账户状态计算奖励。

环境支持：

- 市场类型: 美股、中国股票、ETF、加密货币、外汇等。
- 频率: 日线、分钟、秒级、毫秒级，取决于数据源。
- 数据源: Yahoo Finance、Alpaca、WRDS、Tushare、AkShare、Binance、CCXT、Polygon、Alpha Vantage 等。
- 特征: OHLCV、技术指标、基本面、新闻情绪、社交媒体、ESG、Google Trends。
- 交易约束: 交易成本、非负现金、是否允许卖空、是否允许融资。
- 风控指标: 用 VIX 替代 turbulence index 以提高实时性。

### 3.3 训练-测试-交易设置

FinRL-Meta 强调动态数据集和滚动窗口。典型流程：

1. 用过去 `N` 天数据训练 agent。
2. 用接下来 `S` 天数据验证并调参。
3. 用 `N + S` 天重新训练。
4. 在下一天 paper trading。
5. 窗口向前滚动一天，重复。

这样做比一次性 train/test split 更接近真实部署，因为市场分布会变化，模型需要周期性更新。

### 3.4 状态、动作、奖励设置

状态：

- 账户现金、持仓、市价。
- OHLCV。
- 技术指标，如 MACD、RSI、CCI、ADX。
- 风险指标，如 VIX。
- 可选的新闻情绪、社交媒体特征、基本面数据。

动作：

- 单股票买/卖/持有。
- 多股票买卖向量。
- 组合配置权重。
- 高频或订单簿环境中可扩展为限价单、撤单、订单大小。

奖励：

- 组合累计收益。
- 日收益或对数收益。
- 扣除交易成本后的净收益。
- 可加入波动、回撤、VIX 风控惩罚。

### 3.5 实验设置与结果

股票交易任务：

- 数据: DJIA 30 成分股。
- 特征: MACD、RSI、CCI、ADX 等。
- 算法: A2C、DDPG、TD3、PPO、SAC。
- 训练期: 示例中使用 2011-01-01 到 2021-07-01。
- 交易期: 2021-07-01 到 2022-11-01。
- 结果: 示例中 A2C 收益约 0.102，高于 DJI 的 0.030。

实时 paper trading：

- 数据: Alpaca 分钟级数据。
- 机制: 每天滚动训练、验证、重训、paper trading。
- 对比: PPO 与 random forest。

Ensemble strategy：

- 基础算法: PPO、A2C、DDPG。
- 方法: 滚动窗口选择验证集表现最好的 agent。
- 结果: ensemble 收益约 0.157，高于 DJI 的 0.068。

### 3.6 不足之处

- 数据源多不等于数据质量自动可靠，仍需检查复权、停牌、缺失、时区和交易日历。
- 动态数据集提高真实感，但也增加了工程复杂度和可复现难度。
- paper trading 比回测强，但仍不等同实盘。
- VIX 比 turbulence 更快，但主要适合美股市场，对 A 股、港股、加密资产需要替代风险指标。
- 高维环境和多源特征会放大过拟合。
- 论文中的示例结果仍应视为 benchmark，而不是稳定 alpha 证明。

## 4. FinRL-X 论文详细总结

### 4.1 使用的方法

FinRL-X 的方法是 deployment-aware + weight-centric trading architecture。它认为研究代码常见问题不是模型不能跑，而是回测、paper trading、实盘之间接口不一致。

FinRL-X 把策略统一为目标组合权重：

```text
w_t = R_t(T_t(A_t(S_t(X_t))))
```

其中：

- `S_t`: stock selection，选股。
- `A_t`: allocation，组合配置。
- `T_t`: timing adjustment，择时调整。
- `R_t`: risk overlay，组合层面风险覆盖。
- `w_t`: 最终目标权重。

这个权重向量是回测和执行层唯一需要消费的策略输出。

### 4.2 环境与系统设置

FinRL-X 包含四层：

1. Data layer:
   - 市场数据、基本面、宏观、新闻。
   - 对齐交易日历。
   - 保存原始快照和处理后特征。
   - 用 LLM 处理新闻并转化为情绪信号。

2. Strategy layer:
   - 选股、配置、择时、风险覆盖。
   - 所有模块输出或变换权重。

3. Backtesting layer:
   - 离线回测消费目标权重。
   - 纳入交易成本、滑点、再平衡频率。

4. Execution layer:
   - 接入 Alpaca 等 broker。
   - 将目标权重转换为订单。
   - 记录目标权重、实际权重、订单状态、异常。

### 4.3 强化学习设置

FinRL-X 中的 RL 更像“组合配置模块”，而不是直接输出买卖订单。DRL allocator 生成连续组合权重，之后再经过 timing 和 risk overlay。

这种设计的好处：

- 避免 RL 直接面对券商订单细节。
- 回测和实盘都用同一个权重接口。
- 可把规则策略、均值方差、最小方差、DRL 和 LLM 信号放在同一框架比较。
- 风控可以作为后处理模块，而不是强迫 RL 自己学会所有风险约束。

### 4.4 奖励与评估

FinRL-X 论文更强调系统评估，而不是单个 RL reward。它使用的评估指标包括：

- cumulative return。
- annualized return。
- annualized volatility。
- Sharpe。
- Sortino。
- Calmar。
- maximum drawdown。
- drawdown duration。
- turnover。
- target-realized weight tracking error。
- order rejection rate。
- guardrail trigger。

对 RL 模块而言，更合理的训练奖励应该是组合净收益或风险调整净收益：

```text
r_t = log(V_t / V_{t-1})
      - lambda_turnover * sum_i |w_{t,i} - w^-_{t,i}|
      - lambda_vol * realized_vol_t
      - lambda_dd * max(0, drawdown_t - dd_limit)
```

其中 `w^-_t` 是交易前自然漂移后的权重。这个形式和 FinRL-X 的 weight-centric 接口天然匹配。

### 4.5 实验设置与结果

历史回测：

- 时间: 2018-01-07 到 2025-10-24。
- 资产: 美股和 ETF。
- 基准: SPY、QQQ。
- 策略: KAMA、MeanVar、MinVar、Equal、DRL，分别比较是否加入 timing。
- 成本: 论文中提到按边 10 bps 的交易成本。

关键结果：

- DRL without timing: cumulative return 2.33，Sharpe 0.55，max drawdown -0.31。
- DRL with timing: cumulative return 3.03，Sharpe 0.89，max drawdown -0.27。
- Equal with timing、MinVar with timing、MeanVar with timing 都比无 timing 更好。

Paper trading：

- 时间: 2025-10-26 到 2026-03-12。
- Broker: Alpaca paper trading。
- 策略: Rolling Selection + Adaptive Rotation ensemble。
- 结果: 策略总收益约 19.76%，Sharpe 1.96，同期 SPY、QQQ 为负。

### 4.6 不足之处

- paper trading 时间较短，不足以证明长期稳定盈利。
- paper trading 仍没有真实资金心理、真实冲击成本和完全相同的成交约束。
- 论文重点是架构一致性，不是证明 DRL 一定优于所有传统策略。
- 权重接口适合中低频组合调仓，但对高频订单簿交易不够细。
- LLM 新闻情绪模块可能受提示词、数据源延迟和幻觉影响。

## 5. TradingAgents 论文详细总结

### 5.1 使用的方法

TradingAgents 是多智能体 LLM 交易框架，不是传统 RL 环境。它模拟交易公司组织结构，让不同 agent 分别处理不同分析任务：

- Fundamental Analyst: 财务报表、盈利能力、估值、流动性。
- Sentiment Analyst: 社交媒体、Reddit、X/Twitter、情绪分数。
- News Analyst: 新闻、宏观事件、政府公告。
- Technical Analyst: 技术指标、价格趋势、成交量。
- Bull/Bear Researchers: 多空辩论。
- Trader: 综合信息，形成买卖持有决策。
- Risk Management Team: 激进、中性、保守风险观点。
- Fund Manager: 审批最终交易。

方法上使用 ReAct 风格提示，即推理和工具调用结合。它还使用结构化输出维护全局状态，减少长对话中的信息丢失。

### 5.2 环境和实验设置

实验区间：

- 2024-01-01 到 2024-03-29。

资产：

- AAPL、NVDA、MSFT、META、GOOGL、AMZN 等科技股。

数据：

- OHLCV。
- 新闻。
- 社交媒体情绪。
- 内幕交易。
- 财报和公司基本信息。
- 60 个技术指标。

基线：

- Buy and Hold。
- MACD。
- KDJ + RSI。
- ZMR。
- SMA。

指标：

- cumulative return。
- annualized return。
- Sharpe ratio。
- maximum drawdown。

### 5.3 和 RL 的关系

TradingAgents 本身不是 RL reward 驱动。它更适合作为 RL 交易系统的上游分析层：

- 生成新闻摘要。
- 生成基本面观点。
- 生成风险审查。
- 生成结构化情绪和事件特征。
- 辅助解释 RL 策略为什么调仓。

不建议让 LLM agent 直接下单。更稳妥的是：LLM 输出结构化信号，RL 或组合优化模块输出目标权重，执行层负责下单。

### 5.4 结果与不足

论文报告 TradingAgents 在 AAPL、GOOGL、AMZN 上显著优于基线。例如 AAPL 累计收益 26.62%，Sharpe 8.21，最大回撤 0.91%。

但需要谨慎：

- 回测只有约 3 个月。
- LLM 和工具调用成本高，限制了长期回测。
- Sharpe 非常高，可能受短窗口和行情阶段影响。
- 多源数据检索容易引入延迟、缺失和不可复现问题。
- LLM 推理可解释，但不等于因果正确。

## 6. TensorTrade 本地代码详细总结

### 6.1 项目定位

TensorTrade 是一个组件化 RL 交易框架。和 FinRL 相比，它把环境拆得更细：

- `Observer`: 从 DataFeed 生成 observation。
- `ActionScheme`: 把 agent 输出的 action 转换为订单。
- `RewardScheme`: 计算训练奖励。
- `Portfolio`: 管理钱包、资产和净值。
- `Exchange`: 提供价格和成交模拟。
- `Broker`: 接收订单并更新成交。
- `Stopper`: 判断 episode 是否结束。
- `Renderer`: 渲染交易过程。

### 6.2 环境循环

一次 `env.step(action)` 的逻辑是：

1. `ActionScheme.perform()` 调用 `get_orders()`。
2. 生成订单并提交给 `Broker`。
3. `Broker.update()` 通过 `Exchange` 执行。
4. `Portfolio` 更新现金、持仓、净值。
5. `Observer` 生成下一步 observation。
6. `RewardScheme` 根据组合或价格流计算 reward。
7. `Stopper` 判断是否结束。

这套设计适合研究动作空间和奖励函数，因为可以单独替换每个组件。

### 6.3 动作设置

本地 TensorTrade 的默认动作方案包括：

1. BSH:
   - `action_space = Discrete(2)`。
   - 不是显式三动作 buy/sell/hold。
   - 动作代表目标状态，仓位不变时自然就是 hold。
   - 本地代码中 `PBR.on_action()` 把 `action == 0` 映射为 `position = -1`，`action == 1` 映射为 `position = +1`。
   - 因此可以理解为二元仓位目标：现金/空仓 vs 持有资产。

2. SimpleOrders:
   - 动作空间包含不同交易方向、交易比例、订单条件和持续时间。
   - `action == 0` 通常表示不交易。
   - 可以表达 25%、50%、100% 等部分仓位。

3. ManagedRiskOrders:
   - 在订单中加入止损和止盈。
   - 适合让环境处理部分风控，而不是让 agent 从零学会退出。

BSH 的优点是动作空间小、学习快；缺点是容易在两个状态间频繁切换，产生过度交易。

### 6.4 奖励设置

本地 TensorTrade 有四类主要 reward。

#### 6.4.1 SimpleProfit

源码逻辑：

```text
r_t = net_worth_t / net_worth_{t-window} - 1
```

含义：奖励过去窗口内净值增长。

优点：

- 和最终赚钱目标一致。
- 可作为验证指标。

缺点：

- 短窗口可能噪声大。
- 长窗口奖励延迟。
- 如果持仓不变或净值变化弱，信号稀疏。

#### 6.4.2 RiskAdjustedReturns

支持 Sharpe 和 Sortino：

```text
Sharpe = (mean(returns) - risk_free_rate) / std(returns)
Sortino = (mean(returns) - risk_free_rate) / downside_std(returns)
```

优点是关注风险调整收益。缺点是它不适合单步训练奖励，因为需要一段 returns，容易出现奖励延迟、小样本极端值和 reward hacking。

#### 6.4.3 PBR

PBR 是 Position-Based Returns：

```text
R_t = (p_t - p_{t-1}) * x_t
```

其中：

- `p_t`: 当前价格。
- `x_t`: 当前仓位方向，通常 long 为 `+1`，cash/short-like 状态为 `-1`。

本地源码逻辑：

```python
r = price.diff()
position = current_position
reward = position * r
```

PBR 的关键是每一步都有奖励信号，而不是只有交易时才有奖励。

直观解释：

- 持有多头时价格上涨，奖励为正。
- 持有多头时价格下跌，奖励为负。
- 处于现金/空仓状态时价格上涨，奖励为负，表示错过上涨。
- 处于现金/空仓状态时价格下跌，奖励为正，表示躲过下跌。

优点：

- 信号密集，每一步都可学习。
- 适合学习方向预测。
- 比最终收益奖励更容易训练。

缺点：

- 不直接扣手续费。
- 不直接惩罚换手。
- 如果 action 在 long/cash 间频繁切换，PBR 可能仍然鼓励过度交易。
- 如果把 cash 视为 `-1`，本质上接近“看空”奖励，可能和真实现金持仓含义不完全一致。

#### 6.4.4 AdvancedPBR

源码中 AdvancedPBR 公式为：

```text
R_t = pbr_weight * PBR
      + trade_penalty * I(action changed)
      + hold_bonus * I(flat market and not action changed)
```

参数：

- `pbr_weight`: PBR 权重，默认 1.0。
- `trade_penalty`: 换仓惩罚，默认 -0.001。
- `hold_bonus`: 震荡/平坦市场中持有奖励，默认 0.0001。
- `volatility_threshold`: 判断平坦市场的价格变化阈值，默认 0.001。

优点：

- 显式惩罚交易。
- 鼓励震荡市场少动。

缺点：

- 实验日志显示，直接加入交易惩罚只小幅降低交易次数。
- 惩罚系数难调，太小无效，太大可能让模型完全不交易。
- hold bonus 如果设计不好，会鼓励错过趋势行情。

### 6.5 TensorTrade 实验结论

本地 `docs/EXPERIMENTS.md` 的核心发现：

- PPO 在 BTC/USD 上，在 0% 手续费测试下可以获得 +239 美元。
- 同期 Buy-and-Hold 亏损 -355 美元，说明模型有一定方向预测能力。
- 但在 0.1% 手续费下，模型测试 P&L 变为 -650 美元。
- 主要问题是过度交易，约 30 天 2000+ 次交易。
- 手续费成本大于方向预测收益。

重要结论：

```text
交易 RL 不是只要预测方向正确就能赚钱。
如果信号很弱，手续费、滑点、换手率会吞掉全部 alpha。
```

### 6.6 TensorTrade 的不足

- BSH 动作简单但容易过度交易。
- PBR 能学方向，但和净收益目标不完全一致。
- 训练 reward 与最终评估 P&L 可能不一致。
- 需要额外加入最小持仓时间、置信度阈值、手续费、滑点、换手惩罚。
- 默认示例更多用于研究和教学，不是完整实盘系统。
- 对多股票组合、目标权重和真实 broker 执行的一致性不如 FinRL-X。

## 7. RL 奖励函数设计的重点比较

| 奖励函数 | 公式 | 优点 | 主要问题 | 适合用途 |
| --- | --- | --- | --- | --- |
| 净值变化 | `V_t - V_{t-1}` | 直接对应赚钱 | 尺度不稳定，易过度交易 | 简单基线 |
| 对数收益 | `log(V_t/V_{t-1})` | 稳定、可加 | 需额外成本和风险项 | 推荐主收益项 |
| PBR | `(p_t-p_{t-1})*position_t` | 信号密集，易学方向 | 不等于净收益，不惩罚换手 | 方向学习 |
| Sharpe reward | `mean/std` | 风险调整 | 延迟、噪声、易被 hack | 评估指标，不推荐单步训练 |
| Sortino reward | `mean/downside_std` | 只惩罚下行波动 | 同样有延迟和样本问题 | 评估指标 |
| 成本感知收益 | `return - cost` | 接近真实目标 | 成本参数需准确 | 推荐 |
| 风险惩罚收益 | `return - cost - risk` | 更稳健 | 惩罚项难调 | 组合策略 |

## 8. 当前项目建议采用的 RL 环境设置

### 8.1 推荐状态空间

第一版不要过度复杂，建议：

- 账户状态:
  - 当前现金比例。
  - 当前持仓权重。
  - 当前组合净值。
  - 当前浮动盈亏。

- 市场状态:
  - 最近 `N` 根 K 线的收益率，而不是直接价格。
  - 成交量变化率。
  - 波动率。
  - 高低价区间。

- 技术指标:
  - MACD。
  - RSI。
  - ADX。
  - ATR。
  - 均线偏离度。
  - 近 5/10/20 日动量。

- 风险状态:
  - 当前回撤。
  - 近 20 日波动率。
  - VIX 或市场宽基指数波动。
  - 是否处于极端波动 regime。

- 可选 LLM/多 agent 特征:
  - 新闻情绪分数。
  - 基本面质量分数。
  - 风险 agent 输出的风险等级。
  - 事件冲击标签。

### 8.2 推荐动作空间

不建议一开始使用“买/卖多少股”的高维动作。更推荐目标权重：

```text
a_t = target_weight_t
```

单资产：

- 离散版本: `[0%, 25%, 50%, 75%, 100%]`。
- 连续版本: `[0, 1]`。

多资产：

- 输出权重向量 `w_t`。
- 约束 `sum(w_t) <= 1`。
- 不做空时 `w_i >= 0`。
- 保留现金权重。

这样更接近 FinRL-X，能自然对接回测和执行。

### 8.3 推荐奖励函数

建议使用成本感知、换手约束、风险惩罚的对数收益：

```text
r_t =
  log(V_t / V_{t-1})
  - lambda_cost * transaction_cost_t
  - lambda_turnover * turnover_t
  - lambda_dd * max(0, drawdown_t - dd_limit)
  - lambda_vol * realized_vol_t
```

其中：

- `V_t`: 扣除成本后的组合净值。
- `transaction_cost_t`: 手续费 + 滑点 + spread 估计。
- `turnover_t = sum_i |w_{t,i} - w^-_{t,i}|`。
- `drawdown_t`: 当前从历史高点回撤。
- `realized_vol_t`: 最近窗口组合波动率。
- `lambda_*`: 惩罚系数。

第一版可以简化为：

```text
r_t = log(V_t / V_{t-1}) - 0.001 * turnover_t - 0.1 * max(0, drawdown_t - 0.1)
```

这个形式比 PBR 更接近真实交易目标。

### 8.4 为什么不建议只用 Sharpe 作为训练奖励

Sharpe 适合评估，不适合每步训练：

- 单步 Sharpe 没意义。
- 短窗口 Sharpe 噪声很大。
- 长窗口 Sharpe 奖励延迟严重。
- 标准差接近 0 时可能产生极端奖励。
- agent 可能学会少交易甚至不交易来优化指标。

更好的做法是：训练用净收益类 dense reward，验证和模型选择时看 Sharpe、Sortino、Calmar、最大回撤。

### 8.5 如何控制过度交易

TensorTrade 的实验说明，过度交易是核心问题。建议同时使用：

- 奖励中扣除手续费和滑点。
- 奖励中加入换手惩罚。
- 设置最小持仓时间，例如至少持有 3 或 5 个 bar 才能反向。
- 设置最小调仓阈值，例如目标权重变化小于 5% 不交易。
- 使用目标权重而不是 all-in/all-out。
- 降低决策频率，例如日频或 4 小时频，而不是每分钟。
- 训练时使用略高于真实的成本，让模型更保守。
- 评估时强制报告交易次数、换手率、成本占收益比例。

## 9. 不足和风险清单

所有论文和框架共同存在以下风险：

1. 回测过拟合:
   - DRL 参数多，容易记忆历史噪声。
   - 多特征、多算法、多窗口反复调参会产生数据挖掘偏差。

2. 数据泄漏:
   - 指标计算使用未来数据。
   - 财报发布日期和实际可见时间混淆。
   - 使用当前指数成分股回测历史。

3. 成本低估:
   - 手续费、滑点、spread、市场冲击不足。
   - 高频换手下成本会急剧放大。

4. 成交假设不真实:
   - 回测假设按收盘价成交。
   - 未考虑停牌、涨跌停、部分成交、成交量不足。

5. 非平稳:
   - 训练期有效的规律，测试期可能失效。
   - 牛市训练出的策略可能不适合熊市或震荡市。

6. 奖励错配:
   - reward 上升不代表真实 P&L 上升。
   - gross profit reward 会忽略成本。
   - Sharpe reward 可能被 hack。

7. LLM 信号不稳定:
   - 新闻摘要可能延迟。
   - 情绪分数不可复现。
   - LLM 推理有解释性，但不保证预测能力。

## 10. 建议的落地路线

第一阶段：环境和基线。

- 先做单资产或少量资产。
- 使用目标权重动作。
- 奖励用扣成本后的对数收益。
- 基线必须包括 buy-and-hold、等权、均线策略、RSI/MACD 策略。

第二阶段：RL 训练。

- 使用 PPO/A2C 作为离散动作基线。
- 使用 SAC/TD3 作为连续权重基线。
- 做时间序列切分，不做随机切分。
- 使用 walk-forward validation。

第三阶段：风险和交易成本。

- 加入手续费、滑点、spread。
- 加入换手率惩罚。
- 加入最大回撤约束。
- 输出交易次数和成本分析。

第四阶段：多 agent 信号。

- 技术 agent 输出结构化技术评分。
- 新闻 agent 输出事件和情绪评分。
- 基本面 agent 输出质量和估值评分。
- 风险 agent 输出风险等级。
- RL 环境把这些作为状态特征，而不是让 LLM 直接下单。

第五阶段：paper trading。

- 每天或每周滚动训练。
- 记录目标权重、实际权重、滑点、手续费、订单失败。
- 至少跑数月后再判断策略有效性。

## 11. 最关键结论

FinRL 提供了强化学习交易的教学和研究基础；FinRL-Meta 把重点推进到动态数据和市场环境；FinRL-X 进一步强调回测、paper trading 和实盘执行的一致性；TensorTrade 提供了更细粒度的动作和奖励组件；TradingAgents 则适合作为可解释的多源分析层。

真正可用的交易 RL 系统，应当采用以下组合：

```text
DataOps 数据层
  -> Gym/TensorTrade 风格环境
  -> 成本感知 reward
  -> 目标权重动作
  -> Stable-Baselines3 / FinRL 算法训练
  -> FinRL-X 风格回测和执行接口
  -> TradingAgents 风格解释和风险审查
```

其中最重要的是奖励函数和环境设置。只优化毛收益、方向预测或短期 Sharpe 都不够。奖励必须尽量贴近真实净收益，并显式惩罚交易成本、换手、回撤和波动。否则，模型即使在零手续费下学到了方向，也可能在真实交易成本下亏损。

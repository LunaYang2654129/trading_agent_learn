# MySQL Database

本目录用于初始化和维护 `multiple_agent_finance` 的 MySQL 数据库。

## 初始化

```powershell
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```

默认会创建：

- 数据库：`multiple_agent_finance`
- 应用用户：`maf_app`
- 初始密码：`maf_password_change_me`

长期使用时，请先修改 `database/schema.sql` 和 `.env` 中的默认密码。

## 已有数据库迁移

如果数据库已经初始化过，新增 Technical Agent 和单链路行情入库后需要执行：

```powershell
mysql -u root -p < database/migrations/001_add_technical_indicators.sql
mysql -u root -p < database/migrations/002_add_market_bars.sql
```

## 项目连接配置

复制 `.env.example` 为 `.env`，然后调整：

```env
MAF_MYSQL_HOST=127.0.0.1
MAF_MYSQL_PORT=3306
MAF_MYSQL_USER=maf_app
MAF_MYSQL_PASSWORD=maf_password_change_me
MAF_MYSQL_DATABASE=multiple_agent_finance
```

完整图运行并落库：

```powershell
python -m multiple_agent_finance.main --ticker AAPL --save-db
```

本周技术单链路运行、采集行情并落库：

```powershell
python -m multiple_agent_finance.main --mode technical-chain --ticker AAPL --persist-data --save-db
```

# MySQL Database

本目录用于初始化 `multiple_agent_finance` 的 MySQL 数据库。

## 初始化

```powershell
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```

默认会创建：

- 数据库：`multiple_agent_finance`
- 应用用户：`maf_app`
- 初始密码：`maf_password_change_me`

生产或长期使用时，请先修改 `database/schema.sql` 里的默认密码。

## 项目连接配置

复制 `.env.example` 为 `.env`，然后调整：

```env
MAF_MYSQL_HOST=127.0.0.1
MAF_MYSQL_PORT=3306
MAF_MYSQL_USER=maf_app
MAF_MYSQL_PASSWORD=maf_password_change_me
MAF_MYSQL_DATABASE=multiple_agent_finance
```

运行并落库：

```powershell
python -m multiple_agent_finance.main --ticker AAPL --save-db
```

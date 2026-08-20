# 数据库迁移

迁移配置从项目 `settings.database_url` 读取数据库地址，不在此目录保存密码。

```bash
alembic upgrade head
alembic downgrade -1
alembic current
```

# 阶段 1：数据库建模方案

## 目标

使用 SQLAlchemy 2.0 和 Alembic 建立项目核心关系表，并在本机 PostgreSQL 16 + pgvector 环境完成迁移验证。

## 本阶段表结构

- `users`：用户账号基础信息。
- `artists`：歌手基础信息。
- `songs`：歌曲元数据，通过外键关联歌手。
- `playlists`：用户歌单。
- `playlist_songs`：歌单和歌曲的多对多关联及排序位置。
- `tags`：歌曲标签。
- `song_tags`：歌曲和标签的多对多关联。
- `play_records`：用户播放歌曲的时间记录。

## 约束原则

- 主表使用自增整数主键；关联表使用复合主键，阻止重复关联。
- 用户名和标签名唯一。
- 歌单内歌曲位置不能为负数，同一歌单内位置唯一。
- 歌曲时长和热度不能为负数。
- 外键默认限制删除，避免业务删除规则尚未确定时误删关联数据。
- 时间字段由 PostgreSQL 生成带时区时间。

## 延后决策

- `songs.embedding` 和 `knowledge_chunks` 延后到阶段 7。
- 阶段 7 确认实际 embedding 模型和向量维度后，通过独立迁移加入。
- Jamendo 外部 ID、认证字段和业务删除策略在对应功能阶段确认，不在本阶段猜测。

## 验收

1. 进入 `backend/` 后执行 `alembic upgrade head` 可创建全部核心表。
2. PostgreSQL 可查询到表、主键、外键和约束。
3. SQLAlchemy metadata 与迁移后的数据库结构一致。
4. Ruff、mypy 和 pytest 通过。

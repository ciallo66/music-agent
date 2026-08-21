# 阶段 2：用户角色与管理员权限设计

## 角色与状态

- 用户角色：`user`、`admin`。
- 用户状态：`active`、`disabled`。
- 普通注册接口固定创建 `user/active`，请求体不接受角色和状态字段。
- 管理员只能通过服务器或本机交互式脚本创建，不提供公开注册接口。

## 管理员认证

- 管理员使用独立入口 `POST /api/v1/admin/auth/login`。
- 登录成功后仍复用现有 Access Token 和 Refresh Token 轮换机制。
- 刷新与退出复用 `/api/v1/auth/refresh` 和 `/api/v1/auth/logout`。
- 管理员接口通过 `require_admin` 依赖查询数据库中的实时角色和状态。
- JWT 不作为管理员角色的唯一事实来源，避免角色修改后旧 Token 继续越权。

## 禁用规则

- `disabled` 用户不能登录、刷新 Token 或访问需要身份的接口。
- 已签发的 Access Token 在下一次请求时查询数据库状态，因此禁用立即生效。
- 禁用后的 Refresh Token 不能换取新 Token。

## 管理员创建

- 进入 `backend/` 后使用 `python -m scripts.create_admin` 交互式创建。
- 用户名和密码沿用 6～18 位规则并区分大小写。
- 密码使用隐藏输入和二次确认，不通过命令行参数传递。
- 数据库只保存 Argon2id 哈希。

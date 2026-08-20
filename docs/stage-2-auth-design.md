# 阶段 2：双 Token 认证设计

## 用户规则

- 用户名长度为 6～18 位，区分大小写，不额外限制字符组合。
- 密码长度为 6～18 位，区分大小写，不强制大小写、数字或符号组合。
- 请求字段由 Pydantic v2 校验；用户名唯一性和身份验证由 service 处理。
- 数据库只保存 Argon2id 密码哈希，绝不保存或记录明文密码。

## Token 规则

- Access Token 有效期 1 小时，由前端保存在 Pinia 内存并通过 Bearer Header 发送。
- Refresh Token 有效期 3 天，存入 HttpOnly Cookie。
- 数据库只保存 Refresh Token 的 SHA-256 摘要，不保存原始 Token。
- 每次刷新同时轮换 Refresh Token；旧 Token 立即撤销。
- 退出登录撤销当前 Refresh Token 并清除 Cookie。

## Cookie 规则

- `HttpOnly=true`，阻止前端 JavaScript 读取。
- `SameSite=Lax`，减少跨站请求风险。
- 本地 HTTP 开发使用 `Secure=false`；生产 HTTPS 必须通过环境变量设置为 `true`。
- Cookie Path 限制为 `/api/v1/auth`。

## 接口

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

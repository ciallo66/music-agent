# 阶段 3：前端认证联调

## 目标

用一个最小 Vue 3 界面验证浏览器中的完整认证链路，而不是提前实现音乐业务页面。

## 目录边界

- `backend/`：FastAPI 后端及其测试、迁移、脚本和 Python 依赖。
- `frontend/`：独立的 Vue 3 + Vite + TypeScript 应用，单独维护 `package.json`。
- 开发环境由 Vite 把 `/api` 代理到 FastAPI，避免把后端地址写死在页面代码中。
- 生产环境由 Nginx 提供前端静态文件，并把 `/api` 转发到 FastAPI。

## 本阶段页面

- 普通用户登录、注册。
- 管理员登录。
- 登录后的身份信息展示和退出。

## Token 约定

- Access Token 只保存在 Pinia 内存中，不写入 `localStorage`，降低脚本读取风险。
- Refresh Token 继续由后端写入 HttpOnly Cookie，前端 JavaScript 不读取。
- API 返回 401 时，前端最多尝试一次 `/auth/refresh`，成功后重放原请求。
- 页面刷新后，应用先尝试刷新 Token，再决定是否显示已登录状态。

## 暂不包含

歌曲列表、播放器、推荐、后台数据管理等在认证链路通过后分阶段实现。

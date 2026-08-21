# music-agent 前端

Vue 3 + Vite + TypeScript 前端，与仓库根目录的 FastAPI 后端独立管理依赖。

## 本地运行

先进入仓库的后端目录启动服务：

```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

再启动前端：

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 检查

```powershell
npm run build
```

构建会先执行 `vue-tsc` 类型检查，再生成生产文件到 `dist/`。

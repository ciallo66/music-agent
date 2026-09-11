# Agent 工具调用的安全约束

## 目标与边界

在不改变现有 Agent 架构（注册中心 + 编排循环 + SSE）的前提下，只给 Tool 调用补上必要的
安全约束。**不做的事情**：不隐藏任何工具（模型仍能看到并选择全部工具，包括写/删）、
不引入新的 Agent 框架、不改动推荐与业务功能。

## 一、工具标记操作类型

`AgentTool` 新增 `operation` 字段（`ToolOperation`：`READ` / `WRITE` / `DELETE`），
**默认 `READ`**——只读工具沿用默认值即可；写操作显式标注，例如 `create_playlist` 传入
`ToolOperation.WRITE`，于是自动进入"需要用户确认"的流程，无需改动编排层。

`definition()` 保持原样，**不把 operation 发给模型**：模型看到的信息和以前完全一致，
操作类型只用于服务端运行时判定。

## 二、运行时校验链

收到 Tool Call 后，按顺序校验：

| 校验 | 位置 | 失败行为 |
|---|---|---|
| 工具是否存在 | `registry.get()` | 当作工具错误写回，让模型自纠 |
| 参数是否合法 | 各 handler 内的 `model_validate` | 同上（`ValidationError` → `ValueError`） |
| 是否携带身份字段 | `policy.evaluate_tool_call` | `DENY`：拒绝执行并告知模型 |
| 是否使用了未声明的参数 | `policy.evaluate_tool_call` | `DENY`：按工具 schema 的白名单判定 |
| 是否需要用户确认 | `policy.evaluate_tool_call` → `_dispatch_round` | `CONFIRM`：整轮暂缓并发起确认 |

**身份与权限不由模型决定**：`user_id` / `owner_id` / `account_id` / `session_id` 出现在
工具参数里一律拒绝；工具处理器所需的用户身份通过 `MusicAgentTools(db, user_id)` 构造注入，
身份来源只有一处——路由层 `get_current_user` 得到的登录用户。

## 三、高风险操作的确认流程

`WRITE` / `DELETE` 默认需要用户确认（只读工具直接执行）：

1. 编排循环**先评估本轮全部调用**：只要有一个需要确认，**整轮暂缓**（不执行任何工具，
   包括同一响应里的只读调用），避免出现"执行了一半"的状态；
2. 服务端把待确认调用写入 `tool_confirmations` 表（含所属用户、会话、工具名、**参数快照**、
   过期时间），然后逐个发出 `confirmation_required` 事件，事件 `content` 是 JSON 字符串，
   含 `confirmation_id` / `name` / `operation` / `arguments` / `reason`；
3. 本轮结束（发 `end`）；
4. 用户在前端决定后，`POST /api/v1/agent/confirmations` 提交 `{session_id, decisions}`，
   其中每条决定只有 `confirmation_id` 和 `approved`；
5. 服务端按 `confirmation_id` 取出**自己存的参数**，原子地把记录置为已确认/已拒绝
   （`UPDATE ... WHERE status='pending'`，影响行数不为 1 即报 409），确认的调用才执行，
   被拒绝的调用写一条"用户拒绝"结果回上下文，然后继续推理。

**为什么参数以服务端为准**：客户端只能提交 `confirmation_id + approved`，无法替换参数；
因此不存在"用户看到的和实际执行的不是同一次调用"的问题。**防重放**靠原子状态流转：
同一条记录第二次提交会返回 409；**防过期**靠 `expires_at`（`AGENT_CONFIRMATION_TTL_SECONDS`，
默认 600 秒），过期后无法确认，必须让模型重新发起。

同一响应里若出现非法调用（未知工具、身份字段、未声明参数），这些调用不进入确认流程，
而是按普通工具错误写回，让模型自己纠正。

## 四、调用次数上限

沿用上一轮已实现的保护，本次不新增机制：

- `agent_max_tool_rounds`（保险丝，默认 20）；
- `agent_no_progress_limit`（连续重复调用即收尾，默认 2）；
- `agent_total_timeout_seconds`（单轮时间预算，默认 90）。

## 五、测试覆盖（`tests/test_agent_tool_policy.py`）

- 只读工具放行；写/删工具要求确认；已确认后放行；
- 参数含身份字段或工具未声明的字段：拒绝，且**已确认也拒绝**；
- 写/删工具同样出现在 `definitions()` 中（不隐藏工具）；
- 接口级：高风险调用返回 `confirmation_required` 且本轮不执行；
- 接口级：按 `confirmation_id` 确认后才真正执行；
- 接口级：用户拒绝时不执行，模型收到拒绝结果后继续作答；
- 接口级：同一条确认记录重复提交返回 409；参数由服务端记录决定；
- 接口级：参数带 `user_id` 时工具不执行，返回 `tool_error`；
- 接口级（真实写工具 `create_playlist`，`tests/test_agent_write_tool.py`）：确认前**不落库**、
  确认后落库到**当前用户名下**、拒绝不落库、写操作失败**不重试**且只回滚自身。

## 六、未纳入本次范围

- 按工具配置"是否需要确认"的细粒度开关（当前由操作类型统一决定）；
- 写/删工具本身的业务实现（现有工具仍全部只读）；
- 过期确认记录的定期清理（超时记录会留在表中，需要时可加定时任务）。

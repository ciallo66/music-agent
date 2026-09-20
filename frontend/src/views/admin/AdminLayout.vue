<!-- 管理控制台：独立界面外壳。
     与前台工作区是两套壳子：这里只有后台自己的侧栏与顶栏，
     不再套用前台的侧边导航、搜索条与演示横幅（那些在 :global 里被隐藏）。 -->
<template>
  <div class="admin-shell">
    <header class="admin-top">
      <span class="admin-mark" aria-hidden="true">▣</span>
      <div class="admin-title">
        <strong>管理控制台</strong>
        <small>数据维护 · 账号管理 · 导入任务</small>
      </div>
      <span v-if="!auth.canManageData" class="admin-mode">只读</span>
      <span class="admin-user">
        <strong>{{ auth.user?.username ?? '' }}</strong>
        <small>{{ auth.canManageData ? '管理员' : '演示账号' }}</small>
      </span>
    </header>

    <div class="admin-body">
      <aside class="admin-side">
        <nav class="admin-nav">
          <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="admin-link">
            <span aria-hidden="true">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </router-link>
        </nav>

        <div class="admin-side-bottom">
          <!-- 与前台侧栏底部的「进入管理控制台」同一位置，来回切换不用换地方找 -->
          <a
            class="admin-link admin-back"
            href="/"
            :class="{ 'admin-link-loading': leavingConsole }"
            @click="leaveConsole"
          >
            <span aria-hidden="true">←</span>
            <span>返回前台工作区</span>
          </a>
        </div>
      </aside>

      <main class="admin-main">
        <!-- 演示账号进后台：能看数据，但改数据的按钮会被禁用，这里先说明原因 -->
        <p v-if="!auth.canManageData" class="admin-readonly" role="status">
          <strong>只读模式</strong>
          当前账号可以查看后台数据，但不能改动。数据维护入口已禁用，换管理员账号登录后可操作。
        </p>
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
// 返回前台是整页跳转，用这个标记加过渡态（会话由 Refresh Cookie 恢复）
const leavingConsole = ref(false)

// 进入控制台时给 body 打标记：全局样式据此隐藏前台侧栏、搜索条与演示横幅，
// 让后台真的像另一个界面，而不是「同一个壳子换了个路由」。
// 标记打在 body 上——前台的侧栏和内容区是兄弟节点，挂在内容区里管不到侧栏。
function markConsoleShell(active: boolean): void {
  document.body.classList.toggle('admin-console', active)
}

// 在 setup 同步阶段就打标记，而不是等 onMounted：
// 整页跳到 /admin 时，onMounted 晚于浏览器首帧，会先闪一下前台外壳。
markConsoleShell(true)
onBeforeUnmount(() => markConsoleShell(false))

function leaveConsole(event: MouseEvent): void {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  if (leavingConsole.value) return
  leavingConsole.value = true
  markConsoleShell(false)
  window.location.assign('/')
}

const navItems = [
  { to: '/admin', label: '概览', icon: '◧' },
  { to: '/admin/catalog', label: '曲目管理', icon: '♫' },
  { to: '/admin/artists', label: '歌手管理', icon: '☻' },
  { to: '/admin/users', label: '账号管理', icon: '⚇' },
  { to: '/admin/imports', label: '导入任务', icon: '⇪' },
]
</script>

<style scoped>
.admin-shell {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  background: var(--bg);
}
/* 顶栏：后台自己的身份条，替代前台那套搜索条与横幅 */
.admin-top {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  padding: 12px clamp(16px, 2.4vw, 26px);
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(30, 45, 70, 0.9), rgba(19, 29, 47, 0.9));
}
.admin-mark {
  display: grid;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 10px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 15px;
}
.admin-title strong,
.admin-title small {
  display: block;
}
.admin-title strong {
  color: var(--text);
  font-size: 14px;
}
.admin-title small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
}
.admin-mode {
  padding: 2px 8px;
  border: 1px solid rgba(255, 209, 128, 0.4);
  border-radius: 999px;
  color: #ffd180;
  background: rgba(255, 209, 128, 0.12);
  font-size: 10px;
  letter-spacing: 0.08em;
}
.admin-user {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-left: auto;
}
.admin-user strong {
  color: var(--text);
  font-size: 12px;
}
.admin-user small {
  color: var(--text-muted);
  font-size: 11px;
}
.admin-exit {
  padding: 7px 13px;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  font-size: 12px;
  text-decoration: none;
  white-space: nowrap;
}
.admin-exit:hover {
  color: var(--text);
  background: var(--surface-hover);
}
.admin-body {
  display: flex;
  min-height: 0;
  flex: 1;
}
.admin-side {
  display: flex;
  width: 220px;
  flex-shrink: 0;
  flex-direction: column;
  padding: 14px 12px;
  border-right: 1px solid var(--border);
  background: rgba(12, 20, 34, 0.72);
}
.admin-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* 返回入口固定在侧栏底部：与前台「进入管理控制台」同一位置 */
.admin-side-bottom {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.admin-back {
  color: #e8ac60;
  background: rgba(232, 172, 96, 0.08);
}
.admin-back:hover {
  color: #f3bd7d;
  background: rgba(232, 172, 96, 0.16);
}
.admin-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 11px;
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 12px;
  text-decoration: none;
}
.admin-link:hover {
  color: var(--text);
  background: var(--surface-hover);
}
.admin-link.router-link-exact-active {
  color: var(--accent);
  background: var(--accent-soft);
}
.admin-link-loading {
  cursor: wait;
  opacity: 0.72;
}
.admin-main {
  min-width: 0;
  flex: 1;
  overflow-y: auto;
  padding: 22px clamp(18px, 3vw, 34px) 40px;
}
.admin-readonly {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  margin: 0 0 18px;
  padding: 11px 14px;
  border: 1px solid rgba(255, 209, 128, 0.32);
  border-radius: 12px;
  color: var(--text-secondary);
  background: rgba(255, 209, 128, 0.1);
  font-size: 12px;
  line-height: 1.7;
}
.admin-readonly strong {
  color: #ffd180;
  font-size: 11px;
  letter-spacing: 0.08em;
}
</style>

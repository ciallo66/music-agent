<!-- 管理后台外壳：左侧分区导航 + 右侧内容，风格与前台工作区一致。 -->
<template>
  <div class="admin-shell">
    <aside class="admin-side">
      <header class="admin-brand">
        <span class="admin-mark" aria-hidden="true">▣</span>
        <div>
          <strong>管理控制台</strong>
          <small>{{ auth.user?.username ?? '' }}</small>
        </div>
      </header>

      <nav class="admin-nav">
        <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="admin-link">
          <span aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <footer class="admin-foot">
        <router-link class="admin-link" to="/">
          <span aria-hidden="true">←</span>
          <span>返回前台工作区</span>
        </router-link>
      </footer>
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
</template>

<script setup lang="ts">
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

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
  display: grid;
  height: 100vh;
  grid-template-columns: 232px minmax(0, 1fr);
  background: var(--bg, #101827);
}
.admin-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 14px;
  border-right: 1px solid var(--border);
  background: rgba(12, 20, 34, 0.72);
}
.admin-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 6px 14px;
  border-bottom: 1px solid var(--border);
}
.admin-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 15px;
}
.admin-brand strong {
  display: block;
  color: var(--text);
  font-size: 13px;
}
.admin-brand small {
  color: var(--text-muted);
  font-size: 11px;
}
.admin-nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
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
.admin-foot {
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.admin-main {
  min-width: 0;
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

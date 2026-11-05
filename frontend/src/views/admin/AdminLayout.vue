<!-- 管理控制台：独立界面外壳。
     与前台工作区是两套壳子：这里只有后台自己的侧栏与顶栏，
     不再套用前台的侧边导航、搜索条与演示横幅（那些在 :global 里被隐藏）。 -->
<template>
  <div class="admin-shell">
    <header class="admin-top">
      <AppIcon name="shield" :size="16" class="admin-mark" />
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
            <AppIcon :name="item.icon" :size="15" class="admin-link-icon" />
            <span>{{ item.label }}</span>
          </router-link>
        </nav>

        <div class="admin-side-bottom">
          <!-- 与前台侧栏底部的「进入管理控制台」同一位置，来回切换不用换地方找 -->
          <a
            class="admin-link admin-back"
            href="/"
            aria-label="返回前台工作区"
            :class="{ 'admin-link-loading': leavingConsole }"
            @click="leaveConsole"
          >
            <AppIcon name="arrow-left" :size="14" />
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
import AppIcon from '../../components/AppIcon.vue'
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
  { to: '/admin', label: '概览', icon: 'chart' },
  { to: '/admin/catalog', label: '曲目管理', icon: 'library' },
  { to: '/admin/artists', label: '歌手管理', icon: 'user' },
  { to: '/admin/users', label: '账号管理', icon: 'shield' },
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
  background: var(--bg-elevated);
}
.admin-mark {
  flex-shrink: 0;
  padding: 7px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
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
  padding: 1px 6px;
  border: 1px solid rgba(201, 162, 95, 0.4);
  border-radius: var(--radius-sm);
  color: var(--warning);
  background: rgba(201, 162, 95, 0.1);
  font-size: var(--fs-xs);
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
  padding: 5px 9px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
  font-size: var(--fs-xs);
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
  width: 208px;
  flex-shrink: 0;
  flex-direction: column;
  padding: 12px 10px;
  border-right: 1px solid var(--border);
  background: var(--bg-elevated);
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
  color: var(--text-secondary);
  background: var(--surface);
}
.admin-back:hover {
  color: var(--text);
  background: var(--surface-hover);
}
.admin-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 9px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  text-decoration: none;
}
.admin-link-icon {
  color: var(--text-muted);
}
.admin-link:hover {
  color: var(--text);
  background: var(--surface-hover);
}
.admin-link.router-link-exact-active {
  color: var(--text);
  background: var(--surface-raised);
}
.admin-link.router-link-exact-active .admin-link-icon {
  color: var(--accent);
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
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-left: 2px solid var(--warning);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  font-size: var(--fs-xs);
  line-height: 1.7;
}
.admin-readonly strong {
  color: var(--warning);
  font-size: var(--fs-xs);
  font-weight: 500;
}

/* 窄屏：侧栏折成顶部一行，把整个宽度让给表格 */
@media (max-width: 800px) {
  .admin-body {
    flex-direction: column;
  }

  .admin-side {
    width: 100%;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    padding: 8px 10px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .admin-nav {
    flex-direction: row;
    flex-wrap: nowrap;
    gap: 4px;
  }

  .admin-link {
    flex-shrink: 0;
    padding: 6px;
    gap: 6px;
    white-space: nowrap;
  }

  .admin-side-bottom {
    margin: 0 0 0 auto;
    padding: 0;
    border-top: 0;
  }

  .admin-back {
    white-space: nowrap;
  }

  /* 窄屏只保留返回图标，给导航腾出宽度 */
  .admin-back span:last-child {
    display: none;
  }

  .admin-main {
    overflow-x: auto;
    padding: 16px 14px 32px;
  }
}
</style>

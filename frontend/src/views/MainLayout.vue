<!-- 受保护页面的主布局：侧边导航、顶部工具栏与内容区。本平台不托管音频，没有播放器。 -->
<template>
  <div class="app-layout">
    <aside class="sidebar">
      <router-link class="brand" to="/" aria-label="返回首页">
        <span class="brand-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span>
          <strong>智能数据平台</strong>
          <small>数据检索与智能分析</small>
        </span>
      </router-link>

      <nav aria-label="主要导航">
        <p class="nav-label">工作区</p>
        <router-link
          v-for="item in discoveryItems"
          :key="item.to"
          :to="item.to"
          :class="{ 'nav-link-loading': isNavigating && item.to !== route.path }"
          :title="item.requiresAuth && !auth.isAuthenticated ? '登录后使用' : undefined"
          @mouseenter="prefetchRoute(item.to)"
          @focus="prefetchRoute(item.to)"
        >
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span
            v-if="item.requiresAuth && !auth.isAuthenticated"
            class="nav-lock"
            aria-hidden="true"
            >🔒</span
          >
        </router-link>
        <p class="nav-label">个人空间</p>
        <router-link
          v-for="item in personalItems"
          :key="item.to"
          :to="item.to"
          :class="{ 'nav-link-loading': isNavigating && item.to !== route.path }"
          :title="item.requiresAuth && !auth.isAuthenticated ? '登录后使用' : undefined"
          @mouseenter="prefetchRoute(item.to)"
          @focus="prefetchRoute(item.to)"
        >
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span
            v-if="item.requiresAuth && !auth.isAuthenticated"
            class="nav-lock"
            aria-hidden="true"
            >🔒</span
          >
        </router-link>
      </nav>

      <div class="sidebar-bottom">
        <!-- 管理员入口放在用户信息**上面**：靠底、贴着账号区，位置固定；
            从控制台返回时也是回到这里，来回切换不用换地方找。 -->
        <div v-if="auth.isAdmin" class="console-slot">
          <a
            class="console-entry"
            href="/admin"
            :class="{ 'nav-link-loading': enteringConsole }"
            @click="enterConsole"
          >
            <span class="console-mark" aria-hidden="true">▣</span>
            <span class="console-text">
              <strong>管理控制台</strong>
              <small>数据维护与账号管理</small>
            </span>
            <span class="console-arrow" aria-hidden="true">↗</span>
          </a>
        </div>

        <div v-if="auth.user" class="user-card">
          <span class="avatar" aria-hidden="true">{{
            auth.user.username.slice(0, 1).toUpperCase()
          }}</span>
          <span class="user-copy">
            <strong>{{ auth.user.username }}</strong>
            <small>{{ auth.isAdmin ? '管理员' : '智能体用户' }}</small>
          </span>
          <button type="button" aria-label="退出登录" title="退出登录" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <main class="main-content" :class="{ 'main-content--locked': isFullHeightPage }">
      <div class="content-frame">
        <!-- 演示账号横幅：写给访客/面试官看，说明能用什么，而不是罗列不能做什么。
             整页锁一屏的页面（智能体）不显示：它只吃纵向空间，还会把消息区挤扁。 -->
        <div v-if="auth.isDemo && !isFullHeightPage" class="demo-banner" role="status">
          <strong>演示账号</strong>
          <span
            >全部功能可用：收藏、歌单、反馈、智能体对话与收听记录都会真实保存。后台的数据维护入口对该账号保持只读，避免演示数据被改动。</span
          >
        </div>
        <div v-if="!isFullHeightPage" class="workspace-toolbar">
          <form class="quick-search" role="search" @submit.prevent="submitSearch">
            <span aria-hidden="true">⌕</span>
            <input v-model="quickSearch" type="search" placeholder="搜索内容、来源或标签" />
          </form>
          <span class="toolbar-hint">示例数据 · 可检索、可分析</span>
        </div>
        <router-view />
        <footer v-if="!isFullHeightPage" class="site-footer">
          智能数据平台 · 示例数据仅用于检索、分析与演示 · 不提供内容下载或交易
        </footer>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRoute, useRouter } from 'vue-router'
import { isNavigating } from '../router'

interface NavigationItem {
  to: string
  label: string
  icon: string
  requiresAuth?: boolean
}

const discoveryItems: NavigationItem[] = [
  { to: '/', label: '首页', icon: '⌂' },
  { to: '/songs', label: '内容数据', icon: '▦' },
  { to: '/agent', label: '智能体', icon: '✦', requiresAuth: true },
]
const personalItems: NavigationItem[] = [
  { to: '/playlists', label: '我的空间', icon: '▤', requiresAuth: true },
  { to: '/favorites', label: '收藏', icon: '♡', requiresAuth: true },
  { to: '/profile', label: '个人分析', icon: '◫', requiresAuth: true },
]
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const quickSearch = ref('')
// 进入管理控制台是整页跳转（全局替换），用这个标记给入口加过渡态
const enteringConsole = ref(false)
// 整页锁一屏的页面（如智能体对话）：外壳不渲染横幅/工具条/页脚，
// 滚动锁也在渲染阶段就生效 —— 不再等组件 onMounted 才加类，避免切换时先闪一帧错误骨架。
const isFullHeightPage = computed(() => route.meta.fullHeight === true)

// 整页切到管理控制台：前后台是两套布局，用全局替换而不是局部路由切换。
// 会话不会丢——新文档会用 Refresh Cookie 恢复登录态。
function enterConsole(event: MouseEvent): void {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
    return // 保留新标签页打开等浏览器默认行为
  }
  event.preventDefault()
  if (enteringConsole.value) return
  enteringConsole.value = true
  window.location.assign('/admin')
}

// 悬停或聚焦导航时预取目标页面的懒加载 chunk，减少点击后的等待感。
function prefetchRoute(path: string): void {
  const matched = router.resolve(path).matched
  const loader = matched[matched.length - 1]?.components?.default
  if (typeof loader === 'function') {
    void (loader as () => Promise<unknown>)()
  }
}

async function submitSearch(): Promise<void> {
  const query = quickSearch.value.trim()
  await router.push({ name: 'songs', query: query ? { q: query } : undefined })
}

// 先撤销本地认证状态，再返回登录页。
async function logout(): Promise<void> {
  await auth.logout()
  await router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  position: relative;
  z-index: 20;
  display: flex;
  width: 244px;
  flex-shrink: 0;
  flex-direction: column;
  padding: 22px 14px 16px;
  border-right: 1px solid var(--border);
  background:
    linear-gradient(180deg, rgba(34, 50, 76, 0.94), rgba(20, 31, 51, 0.95)), var(--bg-elevated);
  box-shadow: 10px 0 40px rgba(4, 10, 24, 0.12);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 6px 30px;
  color: var(--text);
  text-decoration: none;
}

.brand-wave {
  display: flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border: 1px solid rgba(149, 244, 227, 0.3);
  border-radius: 13px;
  background: linear-gradient(145deg, rgba(110, 231, 210, 0.24), rgba(169, 162, 255, 0.18));
  box-shadow: 0 9px 24px rgba(28, 184, 164, 0.14);
}

.brand-wave i {
  width: 3px;
  border-radius: 4px;
  background: var(--accent);
}

.brand-wave i:nth-child(1) {
  height: 10px;
}

.brand-wave i:nth-child(2) {
  height: 20px;
}

.brand-wave i:nth-child(3) {
  height: 15px;
}

.brand-wave i:nth-child(4) {
  height: 7px;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 15px;
  letter-spacing: -0.01em;
}

.brand small {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 10px;
  letter-spacing: 0.05em;
}

nav {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-label {
  margin: 18px 13px 6px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.nav-label:first-child {
  margin-top: 0;
}

nav a {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 11px;
  color: var(--text-muted);
  font-size: 13px;
  text-decoration: none;
}

.nav-lock {
  margin-left: auto;
  font-size: 11px;
  opacity: 0.72;
}

nav a:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.045);
}

nav a:active {
  transform: scale(0.98);
}

nav a.nav-link-loading {
  cursor: wait;
  opacity: 0.72;
}

nav a.router-link-exact-active {
  border-color: rgba(110, 231, 210, 0.2);
  color: var(--text);
  background: linear-gradient(100deg, rgba(110, 231, 210, 0.18), rgba(111, 183, 255, 0.08));
  box-shadow: inset 3px 0 0 var(--accent);
}

.nav-icon {
  display: grid;
  width: 23px;
  height: 23px;
  flex-shrink: 0;
  place-items: center;
  color: var(--text-secondary);
  font-size: 17px;
}

nav a.router-link-exact-active .nav-icon {
  color: var(--accent);
}

.sidebar-bottom {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.035);
}

.avatar {
  display: grid;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(110, 231, 210, 0.3);
  border-radius: 11px;
  color: var(--accent-strong);
  background: var(--accent-soft);
  font-size: 13px;
  font-weight: 800;
}

.user-copy {
  min-width: 0;
  flex: 1;
}

.user-copy strong,
.user-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-copy strong {
  color: var(--text);
  font-size: 12px;
}

.user-copy small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
}

.user-card button {
  width: 42px;
  height: 30px;
  border: 0;
  border-radius: 9px;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  font-size: 10px;
}

.user-card button:hover {
  color: var(--danger);
  background: rgba(255, 135, 149, 0.1);
}

.main-content {
  min-width: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

/* 整页锁一屏的页面（智能体）：外层不再滚动，滚动只发生在页面内部。
   这两个规则挂在渲染阶段就生效的类上，切换页面时不会先闪一帧错误骨架。 */
.main-content--locked {
  overflow-y: hidden;
}

.main-content--locked .content-frame {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
}

.main-content--locked :deep(.content-frame > *) {
  min-height: 0;
}

/* 演示账号横幅：每页都在，压成一条细带，别抢对话页的纵向空间 */
.demo-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  padding: 6px 12px;
  border: 1px solid rgba(232, 172, 96, 0.4);
  border-radius: 10px;
  color: var(--text-secondary);
  background: rgba(232, 172, 96, 0.1);
  font-size: 11px;
  line-height: 1.6;
}

.demo-banner strong {
  flex: 0 0 auto;
  padding: 2px 8px;
  border-radius: 6px;
  color: #e8ac60;
  background: rgba(232, 172, 96, 0.18);
  font-size: 11px;
}

.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 10px var(--page-gutter) 0;
}

.quick-search {
  display: flex;
  width: min(100%, 380px);
  align-items: center;
  gap: 8px;
  padding: 6px 11px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.045);
  color: var(--text-muted);
}

.quick-search:focus-within {
  border-color: rgba(110, 231, 210, 0.55);
  box-shadow: 0 0 0 3px rgba(110, 231, 210, 0.08);
}

.quick-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: var(--text);
  background: transparent;
  font: inherit;
  font-size: 12px;
}

/* 管理员入口固定在侧栏底部、用户信息上方：靠底、不抢导航，
   与后台里的「返回前台工作区」是同一处位置。 */
.console-slot {
  margin-bottom: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.console-entry {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(232, 172, 96, 0.4);
  border-radius: 12px;
  color: var(--text);
  background: linear-gradient(120deg, rgba(232, 172, 96, 0.16), rgba(232, 172, 96, 0.06));
  text-decoration: none;
}

.console-entry:hover {
  border-color: rgba(232, 172, 96, 0.65);
  background: linear-gradient(120deg, rgba(232, 172, 96, 0.24), rgba(232, 172, 96, 0.1));
}

.console-mark {
  display: grid;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 9px;
  color: #e8ac60;
  background: rgba(232, 172, 96, 0.18);
  font-size: 14px;
}

.console-text {
  min-width: 0;
  flex: 1;
}

.console-text strong,
.console-text small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.console-text strong {
  color: var(--text);
  font-size: 12px;
}

.console-text small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
}

.console-arrow {
  flex-shrink: 0;
  color: #e8ac60;
  font-size: 13px;
}

.console-entry.nav-link-loading {
  cursor: wait;
  opacity: 0.72;
}

.toolbar-hint {
  color: var(--text-muted);
  font-size: 11px;
}

.content-frame {
  width: 100%;
  max-width: var(--content-width);
  min-height: 100%;
  margin: 0 auto;
}

.site-footer {
  padding: 18px var(--page-gutter) 28px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.6;
  text-align: center;
}

/* 平板横屏：收窄侧栏，把宽度让给内容区（与下方 800px 断点不重叠） */
@media (min-width: 801px) and (max-width: 1024px) {
  .sidebar {
    width: 200px;
    padding: 18px 10px 14px;
  }

  .brand {
    margin: 0 4px 22px;
  }

  nav a {
    padding: 9px 10px;
  }
}

@media (max-width: 800px) {
  .app-layout {
    display: block;
  }

  .sidebar {
    position: relative;
    width: 100%;
    height: auto;
    padding: 10px 12px 8px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .brand {
    margin: 0 5px 8px;
  }

  .brand-wave {
    width: 34px;
    height: 34px;
  }

  .brand small,
  .nav-label,
  .sidebar-bottom {
    display: none;
  }

  nav {
    flex-direction: row;
    gap: 5px;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  nav a {
    flex: 0 0 auto;
    gap: 7px;
    padding: 8px 10px;
    white-space: nowrap;
  }

  nav a.router-link-exact-active {
    box-shadow: none;
  }

  .nav-icon {
    width: 18px;
    height: 18px;
    font-size: 15px;
  }

  .main-content {
    height: calc(100vh - 93px);
  }

  .workspace-toolbar {
    display: block;
    padding-top: 12px;
  }

  .quick-search {
    width: 100%;
  }

  .toolbar-hint {
    display: none;
  }
}
</style>

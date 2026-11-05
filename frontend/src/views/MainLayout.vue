<!-- 受保护页面的主布局：侧边导航、顶部工具栏与内容区。本平台不托管音频，没有播放器。 -->
<template>
  <div class="app-layout">
    <aside class="sidebar">
      <router-link class="brand" to="/" aria-label="返回首页">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="brand-copy">
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
          :aria-label="
            item.requiresAuth && !auth.isAuthenticated ? `${item.label}（需要登录）` : item.label
          "
          @mouseenter="prefetchRoute(item.to)"
          @focus="prefetchRoute(item.to)"
        >
          <AppIcon :name="item.icon" :size="16" class="nav-icon" />
          <span>{{ item.label }}</span>
          <AppIcon
            v-if="item.requiresAuth && !auth.isAuthenticated"
            name="lock"
            :size="13"
            class="nav-lock"
          />
        </router-link>
        <p class="nav-label">个人空间</p>
        <router-link
          v-for="item in personalItems"
          :key="item.to"
          :to="item.to"
          :class="{ 'nav-link-loading': isNavigating && item.to !== route.path }"
          :title="item.requiresAuth && !auth.isAuthenticated ? '登录后使用' : undefined"
          :aria-label="
            item.requiresAuth && !auth.isAuthenticated ? `${item.label}（需要登录）` : item.label
          "
          @mouseenter="prefetchRoute(item.to)"
          @focus="prefetchRoute(item.to)"
        >
          <AppIcon :name="item.icon" :size="16" class="nav-icon" />
          <span>{{ item.label }}</span>
          <AppIcon
            v-if="item.requiresAuth && !auth.isAuthenticated"
            name="lock"
            :size="13"
            class="nav-lock"
          />
        </router-link>
        <!-- 窄屏专用：侧栏底部的账号区会隐藏，这里补上登录/控制台/退出入口 -->
        <span class="mobile-account">
          <router-link v-if="!auth.user" to="/login">登录</router-link>
          <template v-else>
            <a v-if="auth.isAdmin" href="/admin">控制台</a>
            <button type="button" @click="logout">退出</button>
          </template>
        </span>
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
            <AppIcon name="shield" :size="16" class="console-mark" />
            <span class="console-text">
              <strong>管理控制台</strong>
              <small>数据维护与账号管理</small>
            </span>
            <AppIcon name="external" :size="13" class="console-arrow" />
          </a>
        </div>

        <div v-if="auth.user" class="user-card">
          <span class="avatar" aria-hidden="true">{{
            auth.user.username.slice(0, 1).toUpperCase()
          }}</span>
          <span class="user-copy">
            <strong>{{ auth.user.username }}</strong>
            <small>{{ auth.isAdmin ? '管理员' : '普通用户' }}</small>
          </span>
          <button type="button" aria-label="退出登录" title="退出登录" @click="logout">退出</button>
        </div>
        <router-link v-else class="login-entry" to="/login">登录 / 注册</router-link>
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
            <AppIcon name="search" :size="14" class="search-icon" />
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
import AppIcon from '../components/AppIcon.vue'

interface NavigationItem {
  to: string
  label: string
  icon: string
  requiresAuth?: boolean
}

const discoveryItems: NavigationItem[] = [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/songs', label: '内容数据', icon: 'library' },
  { to: '/agent', label: '智能体', icon: 'agent', requiresAuth: true },
]
const personalItems: NavigationItem[] = [
  { to: '/playlists', label: '我的空间', icon: 'list', requiresAuth: true },
  { to: '/favorites', label: '收藏', icon: 'heart', requiresAuth: true },
  { to: '/profile', label: '个人分析', icon: 'chart', requiresAuth: true },
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

/* 侧栏：扁平深色，右侧一条 1px 分隔线，不再用整块渐变背景。 */
.sidebar {
  position: relative;
  z-index: 20;
  display: flex;
  width: 232px;
  flex-shrink: 0;
  flex-direction: column;
  padding: 18px 12px 14px;
  border-right: 1px solid var(--border);
  background: var(--bg-elevated);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 4px 24px;
  color: var(--text);
  text-decoration: none;
}

.brand-mark {
  display: flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
}

.brand-mark i {
  width: 2px;
  border-radius: 1px;
  background: var(--accent);
}

.brand-mark i:nth-child(1) {
  height: 8px;
}

.brand-mark i:nth-child(2) {
  height: 16px;
}

.brand-mark i:nth-child(3) {
  height: 12px;
}

.brand-mark i:nth-child(4) {
  height: 5px;
}

.brand-copy strong,
.brand-copy small {
  display: block;
}

.brand-copy strong {
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 0.01em;
}

.brand-copy small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

nav {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.nav-label {
  margin: 16px 8px 6px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.nav-label:first-child {
  margin-top: 0;
}

nav a {
  position: relative;
  display: flex;
  min-height: 36px;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  text-decoration: none;
}

.nav-icon {
  color: var(--text-muted);
}

.nav-lock {
  margin-left: auto;
  color: var(--text-muted);
  opacity: 0.8;
}

nav a:hover {
  color: var(--text);
  background: var(--surface-hover);
}

nav a.nav-link-loading {
  cursor: wait;
  opacity: 0.6;
}

nav a.router-link-exact-active {
  color: var(--text);
  background: var(--surface-raised);
  box-shadow: inset 2px 0 0 var(--accent);
}

nav a.router-link-exact-active .nav-icon {
  color: var(--accent);
}

.sidebar-bottom {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: var(--radius-sm);
}

.avatar {
  display: grid;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  color: var(--text);
  background: var(--surface-raised);
  font-size: var(--fs-xs);
  font-weight: 600;
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
  font-size: var(--fs-xs);
  font-weight: 500;
}

.user-copy small {
  margin-top: 1px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.user-card button {
  height: 28px;
  padding: 0 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  font-size: var(--fs-xs);
}

.user-card button:hover {
  border-color: var(--border);
  color: var(--text);
  background: var(--surface-hover);
}

/* 未登录时侧栏底部给出明确的登录入口，而不是一片空白 */
.login-entry {
  display: flex;
  height: 34px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  font-size: var(--fs-xs);
  text-decoration: none;
}

.login-entry:hover {
  border-color: var(--border-strong);
  color: var(--text);
  background: var(--surface-hover);
}

/* 移动端账号操作：桌面用侧栏底部，窄屏折叠进导航最后一行 */
.mobile-account {
  display: none;
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

/* 演示账号横幅：一条细带，左侧一道强调色，不抢内容注意力 */
.demo-banner {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 14px var(--page-gutter) 0;
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-left: 2px solid var(--accent);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.demo-banner strong {
  flex: 0 0 auto;
  color: var(--text);
  font-size: var(--fs-xs);
  font-weight: 600;
}

.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px var(--page-gutter) 0;
}

.quick-search {
  display: flex;
  width: min(100%, 360px);
  height: 32px;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-muted);
}

.quick-search:focus-within {
  border-color: var(--border-strong);
  background: var(--surface-solid);
}

.search-icon {
  color: var(--text-muted);
}

.quick-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: var(--text);
  background: transparent;
  font: inherit;
  font-size: var(--fs-xs);
}

/* 管理员入口固定在侧栏底部、用户信息上方：靠底、不抢导航，
   与后台里的「返回前台工作区」是同一处位置。 */
.console-slot {
  margin-bottom: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.console-entry {
  display: flex;
  min-height: 40px;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface);
  text-decoration: none;
}

.console-entry:hover {
  border-color: var(--border-strong);
  color: var(--text);
  background: var(--surface-hover);
}

.console-mark {
  color: var(--text-muted);
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
  color: inherit;
  font-size: var(--fs-xs);
  font-weight: 500;
}

.console-text small {
  margin-top: 1px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.console-arrow {
  color: var(--text-muted);
}

.console-entry.nav-link-loading {
  cursor: wait;
  opacity: 0.6;
}

.toolbar-hint {
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.content-frame {
  width: 100%;
  max-width: var(--content-width);
  min-height: 100%;
  margin: 0 auto;
}

.site-footer {
  padding: 20px var(--page-gutter) 28px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
  text-align: center;
}

/* 平板横屏：收窄侧栏，把宽度让给内容区（与下方 800px 断点不重叠） */
@media (min-width: 801px) and (max-width: 1024px) {
  .sidebar {
    width: 196px;
    padding: 16px 10px 12px;
  }

  .brand {
    margin: 0 4px 18px;
  }
}

@media (max-width: 800px) {
  .app-layout {
    display: flex;
    height: 100vh;
    flex-direction: column;
  }

  .sidebar {
    position: relative;
    width: 100%;
    flex-shrink: 0;
    height: auto;
    padding: 10px 12px 8px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .brand {
    margin: 0 4px 8px;
  }

  .brand-mark {
    width: 28px;
    height: 28px;
  }

  .brand small,
  .nav-label,
  .sidebar-bottom {
    display: none;
  }

  /* 窄屏导航换行而不是横向滚动：所有入口直接可见，不用猜右边还有没有内容 */
  nav {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    overflow: visible;
    padding-bottom: 2px;
  }

  nav a {
    flex: 0 0 auto;
    min-height: 32px;
    gap: 6px;
    padding: 5px 9px;
    white-space: nowrap;
  }

  nav a.router-link-exact-active {
    box-shadow: none;
    background: var(--surface-raised);
  }

  .main-content {
    flex: 1;
    min-height: 0;
  }

  .mobile-account {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: auto;
    padding: 0 6px;
    color: var(--text-muted);
    font-size: var(--fs-xs);
  }

  .mobile-account a,
  .mobile-account button {
    padding: 0;
    border: 0;
    color: inherit;
    background: transparent;
    font-family: inherit;
    font-size: inherit;
    text-decoration: none;
    cursor: pointer;
  }

  .mobile-account a:hover,
  .mobile-account button:hover {
    color: var(--text);
  }

  .demo-banner {
    margin: 12px 16px 0;
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

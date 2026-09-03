<!-- 受保护页面的主布局：侧边导航、内容区和全局播放器。 -->
<template>
  <div class="app-layout" :class="{ 'has-player': player.currentSong }">
    <aside class="sidebar">
      <router-link class="brand" to="/" aria-label="返回首页">
        <span class="brand-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span>
          <strong>Music Agent</strong>
          <small>AI 音乐发现平台</small>
        </span>
      </router-link>

      <nav aria-label="主要导航">
        <p class="nav-label">发现音乐</p>
        <router-link v-for="item in discoveryItems" :key="item.to" :to="item.to">
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
        <p class="nav-label">我的空间</p>
        <router-link v-for="item in personalItems" :key="item.to" :to="item.to">
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
        <template v-if="auth.isAdmin">
          <p class="nav-label">管理</p>
          <router-link to="/admin/imports">
            <span class="nav-icon" aria-hidden="true">↥</span>
            <span>数据导入</span>
          </router-link>
        </template>
      </nav>

      <div class="sidebar-bottom">
        <div v-if="auth.user" class="user-card">
          <span class="avatar" aria-hidden="true">{{
            auth.user.username.slice(0, 1).toUpperCase()
          }}</span>
          <span class="user-copy">
            <strong>{{ auth.user.username }}</strong>
            <small>{{ auth.isAdmin ? '管理员' : '音乐探索者' }}</small>
          </span>
          <button type="button" aria-label="退出登录" title="退出登录" @click="logout">↗</button>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <div class="content-frame"><router-view /></div>
    </main>
    <GlobalPlayer />
  </div>
</template>

<script setup lang="ts">
import GlobalPlayer from '../components/GlobalPlayer.vue'
import { useAuthStore } from '../stores/auth'
import { usePlayerStore } from '../stores/player'
import { useRouter } from 'vue-router'

interface NavigationItem {
  to: string
  label: string
  icon: string
}

const discoveryItems: NavigationItem[] = [
  { to: '/', label: '首页', icon: '⌂' },
  { to: '/songs', label: '音乐库', icon: '♫' },
  { to: '/search', label: '搜索', icon: '⌕' },
  { to: '/agent', label: 'AI 助手', icon: '✦' },
]
const personalItems: NavigationItem[] = [
  { to: '/playlists', label: '我的歌单', icon: '▤' },
  { to: '/favorites', label: '收藏', icon: '♡' },
  { to: '/profile', label: '音乐画像', icon: '◫' },
]
const auth = useAuthStore()
const player = usePlayerStore()
const router = useRouter()

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
  backdrop-filter: blur(24px);
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

nav a:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.045);
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
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 9px;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
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

.content-frame {
  width: 100%;
  max-width: var(--content-width);
  min-height: 100%;
  margin: 0 auto;
}

.has-player .main-content {
  padding-bottom: 82px;
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

  .has-player .main-content {
    padding-bottom: 110px;
  }
}
</style>

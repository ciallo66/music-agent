<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="logo">🎵 Music Agent</div>
      <nav>
        <router-link to="/">首页</router-link>
        <router-link to="/songs">音乐库</router-link>
        <router-link to="/playlists">我的歌单</router-link>
        <router-link to="/favorites">收藏</router-link>
        <router-link to="/search">搜索</router-link>
        <router-link to="/agent">AI 助手</router-link>
        <router-link v-if="auth.isAdmin" to="/admin/imports">数据导入</router-link>
      </nav>
      <div class="sidebar-bottom">
        <div class="user-info" v-if="auth.user">
          <span class="username">{{ auth.user.username }}</span>
          <span class="role">{{ auth.isAdmin ? '管理员' : '普通用户' }}</span>
        </div>
        <button @click="logout">退出</button>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
    <GlobalPlayer />
  </div>
</template>

<script setup lang="ts">
import GlobalPlayer from '../components/GlobalPlayer.vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
const auth = useAuthStore()
const router = useRouter()
async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  padding-bottom: 64px;
}
.sidebar {
  width: 224px;
  background: linear-gradient(180deg, var(--bg-elevated), var(--bg));
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  flex-shrink: 0;
}
.logo {
  padding: 4px 22px 28px;
  font-size: 16px;
  font-weight: 700;
  color: var(--accent-strong);
}
nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
nav a {
  margin: 0 10px;
  padding: 11px 14px;
  border-radius: 10px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
}
nav a:hover {
  color: var(--text);
  background: var(--surface-hover);
}
nav a.router-link-active {
  color: var(--text-on-accent);
  background: var(--accent-soft);
}
.sidebar-bottom {
  padding: 16px 20px 0;
  border-top: 1px solid var(--border);
}
.user-info {
  margin-bottom: 12px;
}
.username {
  display: block;
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}
.role {
  color: var(--accent-strong);
  font-size: 12px;
}
.sidebar-bottom button {
  width: 100%;
  padding: 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
}
.sidebar-bottom button:hover {
  color: var(--text);
}
.main-content {
  flex: 1;
  min-width: 0;
  background: transparent;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
@media (max-width: 760px) {
  .app-layout {
    display: block;
    padding-bottom: 104px;
  }
  .sidebar {
    width: 100%;
    height: auto;
    padding: 12px;
    flex-direction: row;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 900;
  }
  .logo {
    padding: 0 10px;
  }
  nav {
    flex-direction: row;
    overflow-x: auto;
  }
  nav a {
    margin: 0;
    white-space: nowrap;
  }
  .sidebar-bottom {
    display: none;
  }
  .main-content {
    height: calc(100vh - 64px);
  }
}
</style>

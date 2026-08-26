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
  min-height: 100vh;
  padding-bottom: 64px;
}
.sidebar {
  width: 200px;
  background: #0e0f12;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  flex-shrink: 0;
}
.logo {
  padding: 0 20px 24px;
  font-size: 15px;
  font-weight: 700;
  color: #59e2a4;
}
nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
nav a {
  padding: 10px 20px;
  color: #858a96;
  text-decoration: none;
  font-size: 14px;
}
nav a:hover {
  color: #f0f1f3;
}
nav a.router-link-active {
  color: #59e2a4;
  background: rgba(89, 226, 164, 0.08);
}
.sidebar-bottom {
  padding: 16px 20px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.user-info {
  margin-bottom: 12px;
}
.username {
  display: block;
  color: #f0f1f3;
  font-size: 14px;
  font-weight: 600;
}
.role {
  color: #59e2a4;
  font-size: 12px;
}
.sidebar-bottom button {
  width: 100%;
  padding: 8px;
  background: #16181e;
  border: 1px solid #292c34;
  border-radius: 8px;
  color: #858a96;
  cursor: pointer;
}
.sidebar-bottom button:hover {
  color: #f0f1f3;
}
.main-content {
  flex: 1;
  background: #08090c;
  overflow-y: auto;
}
</style>

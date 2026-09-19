<!-- 无权限页：普通账号访问 /admin 时给出明确说明与出路，而不是静默跳回首页。 -->
<template>
  <section class="no-permission-page">
    <div class="no-permission-card page-surface">
      <span class="no-permission-icon" aria-hidden="true">⛨</span>
      <p class="eyebrow">管理后台</p>
      <h1>这个页面需要管理员账号</h1>
      <p class="description">
        内容库、收藏、歌单、个人分析与智能体对本账号全部开放； 数据维护入口只对内网管理员账号开放。
      </p>
      <div class="actions">
        <router-link class="primary-link" to="/songs">返回内容库 <span>→</span></router-link>
        <button type="button" class="secondary-link" @click="switchAccount">切换账号</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

// 退出当前账号并回到登录页，方便直接换成管理员账号。
async function switchAccount(): Promise<void> {
  await auth.logout()
  await router.push({ name: 'login' })
}
</script>

<style scoped>
.no-permission-page {
  display: grid;
  min-height: 100%;
  place-items: center;
  padding: var(--page-gutter);
}

.no-permission-card {
  width: min(100%, 620px);
  padding: clamp(30px, 6vw, 60px);
  text-align: center;
}

.no-permission-icon {
  display: grid;
  width: 62px;
  height: 62px;
  place-items: center;
  margin: 0 auto 22px;
  border: 1px solid rgba(169, 162, 255, 0.32);
  border-radius: 20px;
  color: var(--accent-purple, #a9a2ff);
  background: rgba(169, 162, 255, 0.14);
  font-size: 26px;
}

.eyebrow {
  margin: 0 0 12px;
  color: var(--accent-purple, #a9a2ff);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(24px, 4vw, 34px);
  letter-spacing: -0.04em;
}

.description {
  max-width: 440px;
  margin: 16px auto 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.8;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 26px;
}

.actions a,
.actions button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  padding: 0 17px;
  border-radius: 11px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.primary-link {
  gap: 14px;
  color: var(--text-on-accent);
  background: var(--accent);
}

.secondary-link {
  border: 1px solid var(--border-strong);
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.04);
  font-family: inherit;
}

.secondary-link:hover {
  color: var(--text);
}

.hint-note {
  margin: 22px 0 0;
  color: var(--text-muted);
  font-size: 10px;
}
</style>

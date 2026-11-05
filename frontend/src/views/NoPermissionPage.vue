<!-- 无权限页：普通账号访问 /admin 时给出明确说明与出路，而不是静默跳回首页。 -->
<template>
  <section class="no-permission-page">
    <div class="no-permission-card">
      <p class="eyebrow">管理后台</p>
      <h1>这个页面需要管理员账号</h1>
      <p class="description">
        内容库、收藏、歌单、个人分析与智能体对本账号全部开放； 数据维护入口只对内网管理员账号开放。
      </p>
      <div class="actions">
        <router-link class="primary-link" to="/songs">返回内容库</router-link>
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
  width: min(100%, 520px);
  padding: clamp(28px, 5vw, 48px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(20px, 3vw, 26px);
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: -0.01em;
}

.description {
  max-width: 420px;
  margin: 12px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.8;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
}

.actions a,
.actions button {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: inherit;
  font-size: var(--fs-xs);
  text-decoration: none;
}

.primary-link {
  color: var(--text-on-accent);
  background: var(--accent);
}

.primary-link:hover {
  background: var(--accent-strong);
}

.secondary-link {
  border: 1px solid var(--border-strong);
  color: var(--text-secondary);
}

.secondary-link:hover {
  color: var(--text);
  background: var(--surface-hover);
}
</style>

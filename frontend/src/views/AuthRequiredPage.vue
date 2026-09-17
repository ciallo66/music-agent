<!-- 受保护功能的展示页：保留应用布局，只说明登录要求，不强制弹出登录框。 -->
<template>
  <section class="auth-required-page">
    <div class="auth-required-card page-surface">
      <span class="auth-required-icon" aria-hidden="true">◈</span>
      <p class="eyebrow">需要登录</p>
      <h1>{{ pageTitle }}</h1>
      <p class="description">
        这个功能需要登录后才能使用。你可以先浏览公开内容，登录后即可继续当前操作。
      </p>
      <div class="actions">
        <router-link class="primary-link" :to="loginTarget">登录后继续 <span>→</span></router-link>
        <router-link class="secondary-link" to="/songs">先浏览公开数据</router-link>
      </div>
      <p class="privacy-note">登录只用于保存个人偏好、收藏和工作区记录。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const pageTitle = computed(() => {
  const title = typeof route.query.title === 'string' ? route.query.title : ''
  return title || '登录后使用智能体工作区'
})
const loginTarget = computed(() => ({
  name: 'login',
  query: { redirect: typeof route.query.redirect === 'string' ? route.query.redirect : '/' },
}))
</script>

<style scoped>
.auth-required-page {
  display: grid;
  min-height: 100%;
  place-items: center;
  padding: var(--page-gutter);
}

.auth-required-card {
  width: min(100%, 640px);
  padding: clamp(30px, 6vw, 64px);
  text-align: center;
}

.auth-required-icon {
  display: grid;
  width: 62px;
  height: 62px;
  place-items: center;
  margin: 0 auto 22px;
  border: 1px solid rgba(110, 231, 210, 0.3);
  border-radius: 20px;
  color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 16px 36px rgba(22, 186, 165, 0.14);
  font-size: 26px;
}

.eyebrow {
  margin: 0 0 12px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(25px, 4vw, 38px);
  letter-spacing: -0.04em;
}

.description {
  max-width: 460px;
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
  margin-top: 28px;
}

.actions a {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  padding: 0 17px;
  border-radius: 11px;
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
}

.privacy-note {
  margin: 22px 0 0;
  color: var(--text-muted);
  font-size: 10px;
}
</style>

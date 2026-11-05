<!-- 受保护功能的展示页：保留应用布局，只说明登录要求，不强制弹出登录框。 -->
<template>
  <section class="auth-required-page">
    <div class="auth-required-card">
      <p class="eyebrow">需要登录</p>
      <h1>{{ pageTitle }}</h1>
      <p class="description">
        这个功能需要登录后才能使用。你可以先浏览公开内容，登录后即可继续当前操作。
      </p>
      <div class="actions">
        <router-link class="primary-link" :to="loginTarget">登录后继续</router-link>
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

// 按用户刚才想去的页面给出具体标题；没有匹配时用一句通用说明。
const PAGE_TITLES: Record<string, string> = {
  '/agent': '登录后使用智能体工作区',
  '/playlists': '登录后查看我的空间',
  '/favorites': '登录后查看收藏',
  '/profile': '登录后查看个人分析',
  '/admin': '登录后进入管理工作区',
}

const pageTitle = computed(() => {
  const title = typeof route.query.title === 'string' ? route.query.title : ''
  if (title) return title
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  const path = redirect.split('?')[0]
  return PAGE_TITLES[path] ?? '登录后继续使用该功能'
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

.actions a {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border-radius: var(--radius-sm);
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

.privacy-note {
  margin: 20px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
</style>

<!-- 未知路径：给出明确说明和两个出口，而不是空白页。 -->
<template>
  <section class="not-found-page">
    <div class="not-found-card">
      <p class="code numeric">404</p>
      <h1>页面不存在</h1>
      <p class="description">地址可能输错了，或者这条内容已经被移动。</p>
      <div class="actions">
        <router-link class="primary-link" to="/">返回首页</router-link>
        <router-link class="secondary-link" to="/songs">浏览内容数据</router-link>
      </div>
    </div>
  </section>
</template>

<style scoped>
.not-found-page {
  display: grid;
  min-height: 100%;
  place-items: center;
  padding: var(--page-gutter);
}

.not-found-card {
  width: min(100%, 520px);
  padding: clamp(28px, 5vw, 48px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.code {
  margin: 0 0 8px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  letter-spacing: 0.08em;
}

h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(20px, 3vw, 26px);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.description {
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
</style>

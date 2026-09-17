<!-- 通用 Markdown 渲染：解析后经 XSS 净化再输出，供智能体回复等富文本场景复用。 -->
<template>
  <div class="markdown-body" v-html="rendered" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const props = defineProps<{ content: string }>()

// 关闭原始 HTML，只放行 Markdown 语法本身，从源头减少注入面。
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

// 外链统一新窗口打开，并阻断 opener 与 referrer。
const defaultLinkOpen = markdown.renderer.rules.link_open
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  tokens[index].attrSet('target', '_blank')
  tokens[index].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen
    ? defaultLinkOpen(tokens, index, options, env, self)
    : self.renderToken(tokens, index, options)
}

// 渲染结果统一净化，避免模型输出里的脚本或事件属性进入页面。
const rendered = computed(() =>
  DOMPurify.sanitize(markdown.render(props.content ?? ''), { USE_PROFILES: { html: true } }),
)
</script>

<style scoped>
/* v-html 渲染出的元素不带 scoped 属性，因此内容样式必须用 :deep() 命中。 */
.markdown-body {
  color: var(--text);
  font-size: 14px;
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.markdown-body :deep(> :first-child) {
  margin-top: 0;
}

.markdown-body :deep(> :last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 18px 0 10px;
  color: var(--text);
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

.markdown-body :deep(h1) {
  font-size: 19px;
}

.markdown-body :deep(h2) {
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  font-size: 17px;
}

.markdown-body :deep(h3) {
  font-size: 15px;
}

.markdown-body :deep(h4) {
  color: var(--text-secondary);
  font-size: 14px;
}

.markdown-body :deep(strong) {
  color: var(--accent-strong);
  font-weight: 700;
}

.markdown-body :deep(em) {
  color: var(--text-secondary);
}

.markdown-body :deep(a) {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.markdown-body :deep(a:hover) {
  color: var(--accent-strong);
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0 0 10px;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(li::marker) {
  color: var(--accent);
}

.markdown-body :deep(li > p) {
  margin: 0;
}

/* 行内代码 */
.markdown-body :deep(code) {
  padding: 2px 6px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: rgba(12, 23, 33, 0.55);
  color: var(--accent-strong);
  font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 12.5px;
}

/* 代码块：横向可滚动，避免长行撑破气泡 */
.markdown-body :deep(pre) {
  margin: 0 0 12px;
  padding: 13px 15px;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(9, 17, 27, 0.72);
  line-height: 1.6;
}

.markdown-body :deep(pre code) {
  padding: 0;
  border: none;
  border-radius: 0;
  background: none;
  color: var(--text-secondary);
  font-size: 12.5px;
}

.markdown-body :deep(blockquote) {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  background: var(--accent-soft);
  color: var(--text-secondary);
}

.markdown-body :deep(blockquote > :last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(hr) {
  margin: 16px 0;
  border: none;
  border-top: 1px solid var(--border);
}

/* 表格：外层可滚动，窄屏不破坏布局 */
.markdown-body :deep(table) {
  display: block;
  width: 100%;
  margin: 0 0 12px;
  overflow-x: auto;
  border-collapse: collapse;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 12px;
  border: 1px solid var(--border);
  text-align: left;
}

.markdown-body :deep(th) {
  background: rgba(110, 231, 210, 0.08);
  color: var(--accent-strong);
  font-weight: 700;
}
</style>

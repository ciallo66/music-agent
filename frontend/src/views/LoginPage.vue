<!-- 登录 / 注册：左侧说明产品能做什么，右侧是固定宽度的表单。
     布局要点：表单区宽度恒定、演示入口常驻，切换登录/注册时卡片高度不跳动。 -->
<template>
  <main class="login-page">
    <section class="brand-panel">
      <div class="brand-inner">
        <div class="brand-lockup">
          <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
          <span class="brand-name">
            <strong>智能数据平台</strong>
            <small>数据检索与智能分析</small>
          </span>
        </div>

        <div class="brand-copy">
          <h1>检索、分析、问答，<br />在同一处完成</h1>
          <p class="brand-lead">
            以音乐数据为示例：结构化特征、可解释推荐和对话式取数，所有结果都能回到原始字段核对。
          </p>
          <ul class="brand-points">
            <li><AppIcon name="check" :size="14" />智能体调用数据工具，调用过程可见</li>
            <li><AppIcon name="check" :size="14" />推荐理由与音频特征可追溯到数据源</li>
            <li><AppIcon name="check" :size="14" />个人分析只使用你自己的行为记录</li>
          </ul>
        </div>

        <p class="brand-source">数据来源：AcousticBrainz · MusicBrainz · 不托管音频</p>
      </div>
    </section>

    <section class="auth-panel">
      <div class="auth-inner">
        <header class="auth-copy">
          <h2>{{ panelTitle }}</h2>
          <span>{{ panelDescription }}</span>
        </header>

        <div class="auth-card">
          <div class="mode-switch" role="tablist" aria-label="登录或注册">
            <button
              v-for="item in modes"
              :key="item.value"
              type="button"
              role="tab"
              :aria-selected="mode === item.value"
              :class="{ active: mode === item.value }"
              @click="changeMode(item.value)"
            >
              {{ item.label }}
            </button>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent="submit"
          >
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="form.username"
                maxlength="18"
                autocomplete="username"
                placeholder="4–18 位，支持字母数字下划线"
              />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                maxlength="18"
                :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
                placeholder="4–18 位"
                show-password
                type="password"
                @keyup.enter="submit"
              />
            </el-form-item>
            <el-button
              class="submit-button"
              :loading="submitting"
              native-type="submit"
              type="primary"
            >
              {{ submitLabel }}
            </el-button>
          </el-form>

          <p class="demo-divider"><span>或</span></p>

          <!-- 演示入口常驻：切换登录/注册时不移除，卡片高度因此保持稳定 -->
          <el-button
            class="demo-button"
            :loading="demoLoading"
            native-type="button"
            @click="enterDemo"
          >
            进入演示账号
          </el-button>
          <p class="demo-hint">无需注册即可体验收藏、歌单、反馈与智能体对话。</p>
        </div>

        <p class="security-note">登录状态通过安全令牌维护，请勿在公共设备保存密码。</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/feedback'

type Mode = 'login' | 'register'

// 只有登录和注册两种：是不是管理员由账号角色决定，不再走单独入口
const modes: Array<{ value: Mode; label: string }> = [
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' },
]
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const mode = ref<Mode>('login')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const demoLoading = ref(false)

// 演示凭证必须与后端 DEMO_USERNAME / DEMO_PASSWORD 一致。
// 换环境时改前端 .env 的 VITE_DEMO_USERNAME / VITE_DEMO_PASSWORD，
// 再用 `python -m scripts.ensure_demo_account` 把库里的账号对上。
const DEMO_CREDENTIALS = {
  username: import.meta.env.VITE_DEMO_USERNAME ?? 'demo',
  password: import.meta.env.VITE_DEMO_PASSWORD ?? 'demo1234',
}
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 4, max: 18, message: '用户名需为 4–18 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 4, max: 18, message: '密码需为 4–18 位', trigger: 'blur' },
  ],
}
const panelTitle = computed(
  () => ({ login: '继续使用智能体', register: '创建你的工作区' })[mode.value],
)
const panelDescription = computed(
  () =>
    ({
      login: '登录后继续使用个人工作区',
      register: '注册后即可保存偏好、整理内容并生成个人分析',
    })[mode.value],
)
const submitLabel = computed(() => ({ login: '登录', register: '创建账号' })[mode.value])

// 切换认证模式，并清除旧模式遗留的校验提示。
function changeMode(nextMode: Mode): void {
  mode.value = nextMode
  formRef.value?.clearValidate()
}

// 一键进入演示账号：用配置里的演示凭证登录并直接进入工作区。
async function enterDemo(): Promise<void> {
  if (demoLoading.value || submitting.value) return
  demoLoading.value = true
  try {
    await auth.login(DEMO_CREDENTIALS.username, DEMO_CREDENTIALS.password)
    showSuccess('已进入演示账号')
    await router.push('/')
  } catch (error) {
    // 凭证对不上时给出可操作的提示，而不是笼统的「不可用」
    showError(error, '演示账号登录失败，请用注册的账号登录或联系管理员')
  } finally {
    demoLoading.value = false
  }
}

// 统一处理登录和注册；管理员与普通用户走同一个入口，角色由账号决定。
async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || submitting.value) return
  submitting.value = true
  try {
    if (mode.value === 'register') {
      await auth.register(form.username, form.password)
      showSuccess('注册成功，请登录')
      changeMode('login')
      return
    }
    await auth.login(form.username, form.password)
    showSuccess(auth.isAdmin ? '已登录管理员账号' : '登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    const target = redirect.startsWith('/') ? redirect : '/'
    await router.push(auth.isAdmin && target === '/' ? '/admin' : target)
  } catch (error) {
    showError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  /* 品牌区弹性、表单区固定：表单卡片不会因为屏宽变化而拉出一片空白 */
  grid-template-columns: minmax(0, 1fr) clamp(400px, 40vw, 520px);
  background: var(--bg);
}

/* 左侧：纯文字说明，没有光晕、插画和大标题字效 */
.brand-panel {
  display: flex;
  align-items: center;
  padding: clamp(32px, 6vw, 80px);
  border-right: 1px solid var(--border);
  background: var(--bg-elevated);
}

.brand-inner {
  display: flex;
  width: 100%;
  max-width: 520px;
  flex-direction: column;
  gap: clamp(32px, 6vh, 72px);
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 10px;
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

.brand-name strong,
.brand-name small {
  display: block;
}

.brand-name strong {
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.brand-name small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.brand-copy h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(28px, 3.4vw, 40px);
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.brand-lead {
  max-width: 460px;
  margin: 16px 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.8;
}

.brand-points {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 26px 0 0;
  padding: 0;
  list-style: none;
}

.brand-points li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.brand-points :deep(.app-icon) {
  margin-top: 3px;
  color: var(--accent);
}

.brand-source {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

/* 右侧：固定宽度表单 */
.auth-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(24px, 4vw, 56px);
}

.auth-inner {
  width: 100%;
  max-width: 340px;
}

.auth-copy h2 {
  margin: 0;
  color: var(--text);
  font-size: var(--fs-xl);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.auth-copy span {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.auth-card {
  margin-top: 22px;
}

.mode-switch {
  display: flex;
  gap: 2px;
  margin-bottom: 18px;
  padding: 2px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
}

.mode-switch button {
  flex: 1;
  height: 30px;
  border: 0;
  border-radius: 3px;
  color: var(--text-muted);
  background: transparent;
  font-size: var(--fs-xs);
  cursor: pointer;
}

.mode-switch button:hover {
  color: var(--text);
}

.mode-switch button.active {
  color: var(--text);
  background: var(--surface-raised);
}

.submit-button {
  width: 100%;
  margin-top: 4px;
}

.demo-divider {
  position: relative;
  margin: 22px 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  text-align: center;
}

.demo-divider::before {
  position: absolute;
  top: 50%;
  left: 0;
  width: 100%;
  border-top: 1px solid var(--border);
  content: '';
}

.demo-divider span {
  position: relative;
  padding: 0 8px;
  background: var(--bg);
}

.demo-button {
  width: 100%;
}

.demo-hint {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.security-note {
  margin: 24px 0 0;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .brand-panel {
    display: none;
  }
}
</style>

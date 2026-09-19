<!-- 登录 / 注册：左侧品牌区只做背景氛围，右侧表单卡片固定宽度并垂直居中。
     布局要点：表单区宽度恒定、演示入口常驻，切换登录/注册时卡片高度不跳动。 -->
<template>
  <main class="login-page">
    <section class="brand-panel" aria-hidden="true">
      <div class="brand-lockup">
        <span class="brand-wave"><i></i><i></i><i></i><i></i></span>
        <span><strong>智能数据平台</strong><small>数据检索与智能分析</small></span>
      </div>
      <div class="brand-halo"></div>
      <div class="brand-copy">
        <p>智能协作平台</p>
        <h1>让数据进入对话<br />让智能体真正工作</h1>
        <span>结构化检索、可解释分析、对话式取数——示例数据均可在线体验。</span>
        <ul class="brand-points">
          <li><i>✦</i>智能体可直接调用数据工具</li>
          <li><i>▦</i>音频特征与推荐理由可追溯</li>
          <li><i>◫</i>个人分析由真实行为数据生成</li>
        </ul>
      </div>
    </section>

    <section class="auth-panel">
      <div class="auth-inner">
        <header class="auth-copy">
          <p>欢迎使用</p>
          <h2>{{ panelTitle }}</h2>
          <span>{{ panelDescription }}</span>
        </header>

        <div class="auth-card page-surface">
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
                size="large"
              />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                maxlength="18"
                :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
                placeholder="4–18 位"
                show-password
                size="large"
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
            一键进入演示账号
          </el-button>
          <p class="demo-hint">无需注册即可体验完整功能：收藏、歌单、反馈与智能体对话。</p>
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
  grid-template-columns: minmax(0, 1fr) clamp(460px, 44vw, 620px);
  background: var(--bg);
}
.brand-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 40px;
  padding: clamp(32px, 4.4vw, 64px);
  overflow: hidden;
  border-right: 1px solid var(--border);
  background: linear-gradient(150deg, rgba(31, 50, 78, 0.92), rgba(17, 26, 45, 0.94));
}
.brand-lockup {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-lockup > span:last-child strong,
.brand-lockup > span:last-child small {
  display: block;
}
.brand-lockup strong {
  color: var(--text);
  font-size: 15px;
}
.brand-lockup small {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 10px;
  letter-spacing: 0.06em;
}
.brand-wave {
  display: flex;
  width: 42px;
  height: 42px;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border: 1px solid rgba(110, 231, 210, 0.3);
  border-radius: 14px;
  background: var(--accent-soft);
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
  height: 22px;
}
.brand-wave i:nth-child(3) {
  height: 16px;
}
.brand-wave i:nth-child(4) {
  height: 7px;
}
/* 柔光背景：填满品牌区，避免大片纯色显得空 */
.brand-halo {
  position: absolute;
  top: 18%;
  left: -12%;
  width: min(78%, 720px);
  aspect-ratio: 1;
  border-radius: 50%;
  background:
    radial-gradient(circle at 62% 38%, rgba(110, 231, 210, 0.22), transparent 58%),
    radial-gradient(circle at 38% 66%, rgba(169, 162, 255, 0.18), transparent 60%);
  filter: blur(6px);
  pointer-events: none;
}
.brand-copy {
  position: relative;
  z-index: 2;
  max-width: 620px;
}
.brand-copy p,
.auth-copy p {
  margin: 0 0 14px;
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.2em;
}
.brand-copy h1 {
  margin: 0;
  color: var(--text);
  font-size: clamp(34px, 3.6vw, 54px);
  line-height: 1.14;
  letter-spacing: -0.04em;
}
.brand-copy > span {
  display: block;
  max-width: 520px;
  margin-top: 20px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.9;
}
.brand-points {
  display: grid;
  gap: 12px;
  margin: 26px 0 0;
  padding: 0;
  list-style: none;
}
.brand-points li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12px;
}
.brand-points i {
  display: grid;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 9px;
  color: var(--accent);
  background: rgba(255, 255, 255, 0.04);
  font-style: normal;
  font-size: 12px;
}
.auth-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(28px, 3.2vw, 48px);
  background: rgba(12, 20, 35, 0.44);
}
/* 表单列宽固定，卡片与文案左对齐同一条竖线 */
.auth-inner {
  width: 100%;
  max-width: 460px;
}
.auth-copy {
  margin-bottom: 22px;
}
.auth-copy h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(24px, 2.4vw, 32px);
  letter-spacing: -0.03em;
}
.auth-copy > span {
  display: block;
  min-height: 18px;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
}
.auth-card {
  padding: 26px;
}
/* 两个模式就两列：多出来的列会让按钮挤在左边、右侧留白 */
.mode-switch {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 4px;
  margin-bottom: 22px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(11, 21, 37, 0.5);
}
.mode-switch button {
  padding: 10px 8px;
  border: 0;
  border-radius: 9px;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  transition:
    color 0.18s ease,
    background 0.18s ease;
}
.mode-switch button:hover:not(.active) {
  color: var(--text);
}
.mode-switch button.active {
  color: var(--text-on-accent);
  background: var(--accent);
  box-shadow: 0 7px 18px rgba(22, 186, 165, 0.18);
  font-weight: 700;
}
.submit-button {
  width: 100%;
  height: 44px;
  margin-top: 4px;
}
.demo-divider {
  position: relative;
  margin: 20px 0 14px;
  color: var(--text-muted);
  font-size: 10px;
  text-align: center;
}
.demo-divider::before,
.demo-divider::after {
  position: absolute;
  top: 50%;
  width: calc(50% - 18px);
  height: 1px;
  background: var(--border);
  content: '';
}
.demo-divider::before {
  left: 0;
}
.demo-divider::after {
  right: 0;
}
/* 次要动作：宽度与主按钮一致，避免卡片内部左右不齐 */
.demo-button {
  width: 100%;
  height: 42px;
}
.demo-hint {
  margin: 10px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.7;
  text-align: center;
}
.security-note {
  margin: 18px 0 0;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.6;
  text-align: center;
}
@media (max-width: 1040px) {
  .login-page {
    grid-template-columns: minmax(0, 1fr) clamp(420px, 52vw, 560px);
  }
}
@media (max-width: 880px) {
  .login-page {
    display: block;
    min-height: 100dvh;
  }
  .brand-panel {
    gap: 26px;
    padding: 30px 24px 38px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .brand-copy h1 {
    font-size: clamp(30px, 7vw, 42px);
  }
  .brand-points {
    display: none;
  }
  .auth-panel {
    padding: 32px 20px 48px;
  }
}
</style>

<!-- 登录、注册和管理员入口共用表单，只切换认证模式与提示文案。 -->
<template>
  <main class="login-page">
    <section class="brand-panel">
      <div class="brand-lockup">
        <span class="brand-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span><strong>智能数据平台</strong><small>数据检索与智能分析</small></span>
      </div>
      <div class="brand-copy">
        <p>智能协作平台</p>
        <h1>让数据进入对话，<br />让智能体真正工作。</h1>
        <span>当前数据仅用于演示，智能体负责检索、分析和组织可解释的结果。</span>
      </div>
      <div class="feature-row">
        <span><i>✦</i> AI 智能体</span><span><i>▦</i> 数据工具</span
        ><span><i>◫</i> 可解释分析</span>
      </div>
      <div class="decor-record" aria-hidden="true"><span>✦</span></div>
    </section>

    <section class="auth-panel">
      <div class="auth-copy">
        <p>欢迎使用</p>
        <h2>{{ panelTitle }}</h2>
        <span>{{ panelDescription }}</span>
      </div>
      <div class="auth-card page-surface">
        <div class="mode-switch" aria-label="登录方式">
          <button
            v-for="item in modes"
            :key="item.value"
            type="button"
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
              placeholder="请输入 6–18 位用户名"
              size="large"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              maxlength="18"
              :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
              placeholder="请输入 6–18 位密码"
              show-password
              size="large"
              type="password"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button class="submit-button" :loading="submitting" native-type="submit" type="primary"
            >{{ submitLabel }} <span v-if="!submitting" aria-hidden="true">→</span></el-button
          >
        </el-form>
        <p class="security-note">
          <span aria-hidden="true">◇</span> 登录状态通过安全令牌维护，请勿在公共设备保存密码。
        </p>
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

type Mode = 'login' | 'register' | 'admin'

const modes: Array<{ value: Mode; label: string }> = [
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' },
  { value: 'admin', label: '管理员' },
]
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const mode = ref<Mode>('login')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 6, max: 18, message: '用户名需为 6–18 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 18, message: '密码需为 6–18 位', trigger: 'blur' },
  ],
}
const panelTitle = computed(
  () =>
    ({ login: '继续使用智能体', register: '创建你的工作区', admin: '进入管理控制台' })[mode.value],
)
const panelDescription = computed(
  () =>
    ({
      login: '登录后继续使用个人工作区',
      register: '注册后即可保存偏好、整理内容并生成个人分析',
      admin: '仅限拥有管理员权限的账号使用',
    })[mode.value],
)
const submitLabel = computed(
  () => ({ login: '登录', register: '创建账号', admin: '管理员登录' })[mode.value],
)

// 切换认证模式，并清除旧模式遗留的校验提示。
function changeMode(nextMode: Mode): void {
  mode.value = nextMode
  formRef.value?.clearValidate()
}

// 统一处理登录、注册和管理员登录，避免三套表单逻辑分叉。
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
    await auth.login(form.username, form.password, mode.value === 'admin')
    showSuccess('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect.startsWith('/') ? redirect : '/')
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
  grid-template-columns: minmax(0, 1.15fr) minmax(440px, 0.85fr);
  overflow: hidden;
}
.brand-panel {
  position: relative;
  display: flex;
  min-height: 100vh;
  justify-content: space-between;
  flex-direction: column;
  padding: clamp(34px, 5vw, 72px);
  overflow: hidden;
  border-right: 1px solid var(--border);
  background:
    radial-gradient(circle at 75% 62%, rgba(110, 231, 210, 0.18), transparent 28%),
    linear-gradient(145deg, rgba(31, 50, 78, 0.9), rgba(20, 30, 52, 0.92));
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
  font-size: 9px;
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
.brand-copy {
  position: relative;
  z-index: 2;
  max-width: 720px;
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
  font-size: clamp(42px, 5.4vw, 76px);
  line-height: 1.08;
  letter-spacing: -0.055em;
}
.brand-copy > span {
  display: block;
  max-width: 570px;
  margin-top: 24px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.9;
}
.feature-row {
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.feature-row > span {
  padding: 8px 13px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.035);
  font-size: 10px;
}
.feature-row i {
  margin-right: 5px;
  color: var(--accent);
  font-style: normal;
}
.decor-record {
  position: absolute;
  right: -110px;
  bottom: -120px;
  display: grid;
  width: 430px;
  height: 430px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 50%;
  background: repeating-radial-gradient(
    circle,
    rgba(255, 255, 255, 0.07) 0 1px,
    rgba(12, 24, 42, 0.32) 2px 12px
  );
  transform: rotate(-12deg);
}
.decor-record span {
  display: grid;
  width: 110px;
  height: 110px;
  place-items: center;
  border-radius: 50%;
  color: var(--text-on-accent);
  background: linear-gradient(145deg, var(--accent), var(--accent-purple));
  font-size: 36px;
}
.auth-panel {
  display: grid;
  min-height: 100vh;
  align-content: center;
  padding: clamp(30px, 5vw, 76px);
  background: rgba(12, 20, 35, 0.44);
  backdrop-filter: blur(18px);
}
.auth-copy {
  width: min(100%, 430px);
  margin: 0 auto 24px;
}
.auth-copy h2 {
  margin: 0;
  color: var(--text);
  font-size: clamp(26px, 3vw, 36px);
  letter-spacing: -0.04em;
}
.auth-copy > span {
  display: block;
  margin-top: 9px;
  color: var(--text-muted);
  font-size: 12px;
}
.auth-card {
  width: min(100%, 430px);
  margin: 0 auto;
  padding: 25px;
}
.mode-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin-bottom: 24px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(11, 21, 37, 0.5);
}
.mode-switch button {
  padding: 9px 7px;
  border: 0;
  border-radius: 9px;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  font-size: 11px;
}
.mode-switch button.active {
  color: var(--text-on-accent);
  background: var(--accent);
  box-shadow: 0 7px 18px rgba(22, 186, 165, 0.18);
  font-weight: 700;
}
.submit-button {
  width: 100%;
  height: 45px;
  margin-top: 7px;
}
.submit-button span span {
  margin-left: 18px;
}
.security-note {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  margin: 18px 0 0;
  color: var(--text-muted);
  font-size: 9px;
  line-height: 1.55;
  text-align: center;
}
@media (max-width: 900px) {
  .login-page {
    display: block;
    overflow-y: auto;
  }
  .brand-panel {
    min-height: 350px;
    padding: 28px 24px 42px;
    gap: 52px;
  }
  .brand-copy h1 {
    font-size: clamp(38px, 10vw, 58px);
  }
  .feature-row {
    display: none;
  }
  .decor-record {
    width: 280px;
    height: 280px;
    right: -100px;
    bottom: -100px;
  }
  .auth-panel {
    min-height: auto;
    padding: 52px 20px;
  }
}
</style>

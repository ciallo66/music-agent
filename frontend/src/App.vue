<script setup lang="ts">
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { useAuthStore } from './stores/auth'

type AuthMode = 'login' | 'register' | 'admin'
interface AuthForm { username: string; password: string }

const auth = useAuthStore()
const mode = ref<AuthMode>('login')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive<AuthForm>({ username: '', password: '' })
const rules: FormRules<AuthForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 6, max: 18, message: '用户名长度为 6–18 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 18, message: '密码长度为 6–18 位', trigger: 'blur' },
  ],
}
const modeLabels: Record<AuthMode, string> = {
  login: '用户登录',
  register: '创建账号',
  admin: '管理员登录',
}

onMounted(() => auth.initialize())

function switchMode(nextMode: AuthMode): void {
  mode.value = nextMode
  form.password = ''
  formRef.value?.clearValidate()
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (mode.value === 'register') {
      await auth.register(form.username, form.password)
      ElMessage.success('注册成功，请登录')
      switchMode('login')
      return
    }
    await auth.login(form.username, form.password, mode.value === 'admin')
    ElMessage.success('登录成功')
  } catch (error) {
    ElMessage.error(auth.errorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function logout(): Promise<void> {
  await auth.logout()
  ElMessage.success('已安全退出')
}
</script>

<template>
  <main class="page-shell">
    <section class="brand-panel">
      <div class="brand-mark" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
      <div>
        <p class="eyebrow">MUSIC AGENT</p>
        <h1>让每一次播放，<br />更懂你的情绪。</h1>
        <p class="brand-copy">AI 驱动的音乐发现平台，从你的喜好出发，找到此刻真正想听的声音。</p>
      </div>
      <div class="feature-row"><span>个性推荐</span><span>AI 歌单</span><span>音乐探索</span></div>
    </section>

    <section class="auth-panel">
      <div v-if="!auth.initialized" class="loading-state"><p>正在恢复登录状态…</p></div>
      <div v-else-if="auth.isAuthenticated" class="profile-card">
        <div class="avatar">{{ auth.user?.username.slice(0, 1).toUpperCase() }}</div>
        <p class="eyebrow">AUTHENTICATED</p>
        <h2>欢迎回来，{{ auth.user?.username }}</h2>
        <p class="profile-meta">{{ auth.isAdmin ? '管理员账号' : '普通用户' }} · 状态正常</p>
        <el-button class="primary-button" type="primary" @click="logout">退出登录</el-button>
      </div>

      <div v-else class="form-card">
        <p class="eyebrow">WELCOME BACK</p>
        <h2>{{ modeLabels[mode] }}</h2>
        <p class="form-hint">{{ mode === 'register' ? '账号和密码均为 6–18 位，区分大小写。' : '输入账号信息以继续探索音乐。' }}</p>
        <div class="mode-switch">
          <button :class="{ active: mode === 'login' }" type="button" @click="switchMode('login')">登录</button>
          <button :class="{ active: mode === 'register' }" type="button" @click="switchMode('register')">注册</button>
          <button :class="{ active: mode === 'admin' }" type="button" @click="switchMode('admin')">管理员</button>
        </div>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" maxlength="18" placeholder="请输入 6–18 位用户名" size="large" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" maxlength="18" placeholder="请输入 6–18 位密码" show-password size="large" type="password" @keyup.enter="submit" />
          </el-form-item>
          <el-button class="primary-button" :loading="submitting" native-type="submit" type="primary">{{ modeLabels[mode] }}</el-button>
        </el-form>
        <p class="security-note">Refresh Token 由 HttpOnly Cookie 安全保存</p>
      </div>
    </section>
  </main>
</template>

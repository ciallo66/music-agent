<template>
  <div class="login-wrap">
    <div class="brand-mark"><span></span><span></span><span></span><span></span></div>
    <h1>Music Agent</h1>
    <p class="sub">让每一次播放，更懂你的情绪。</p>
    <div class="auth-card">
      <div class="mode-switch">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        <button :class="{ active: mode === 'admin' }" @click="mode = 'admin'">管理员</button>
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
            placeholder="6-18位用户名"
            size="large"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            maxlength="18"
            placeholder="6-18位密码"
            show-password
            size="large"
            type="password"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button class="sub-btn" :loading="submitting" native-type="submit" type="primary">{{
          mode === 'login' ? '登录' : mode === 'register' ? '注册' : '管理员登录'
        }}</el-button>
      </el-form>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
type Mode = 'login' | 'register' | 'admin'
const auth = useAuthStore()
const router = useRouter()
const mode = ref<Mode>('login')
const formRef = ref()
const submitting = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 6, max: 18, message: '用户名6-18位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 18, message: '密码6-18位', trigger: 'blur' },
  ],
}
async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (mode.value === 'register') {
      await auth.register(form.username, form.password)
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      return
    }
    await auth.login(form.username, form.password, mode.value === 'admin')
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(auth.errorMessage(e))
  } finally {
    submitting.value = false
  }
}
</script>
<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #08090c;
  padding: 40px 20px;
}
.brand-mark {
  height: 32px;
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 16px;
}
.brand-mark span {
  width: 5px;
  border-radius: 8px;
  background: #59e2a4;
}
.brand-mark span:nth-child(1) {
  height: 12px;
}
.brand-mark span:nth-child(2) {
  height: 27px;
}
.brand-mark span:nth-child(3) {
  height: 20px;
}
.brand-mark span:nth-child(4) {
  height: 9px;
}
h1 {
  color: #f0f1f3;
  font-size: 32px;
  letter-spacing: -0.03em;
  margin: 0 0 8px;
}
.sub {
  color: #858a96;
  margin: 0 0 40px;
  font-size: 15px;
}
.auth-card {
  width: 100%;
  max-width: 400px;
  background: #111215;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 32px;
}
.mode-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin-bottom: 24px;
  padding: 4px;
  border-radius: 10px;
  background: #16181e;
}
.mode-switch button {
  padding: 8px;
  border: 0;
  border-radius: 8px;
  color: #858a96;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
}
.mode-switch button.active {
  color: #08090c;
  background: #59e2a4;
  font-weight: 700;
}
.sub-btn {
  width: 100%;
  height: 44px;
  margin-top: 8px;
  --el-button-bg-color: #59e2a4;
  --el-button-border-color: #59e2a4;
  --el-button-text-color: #07110c;
}
</style>

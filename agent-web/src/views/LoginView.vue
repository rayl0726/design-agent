<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <h2 class="login-title">账号登录</h2>
      </template>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="手机号">
          <el-input
            v-model="form.phone"
            placeholder="请输入手机号"
            maxlength="11"
            clearable
          />
        </el-form-item>

        <el-form-item label="验证码">
          <el-input
            v-model="form.code"
            placeholder="请输入验证码"
            maxlength="6"
            clearable
          >
            <template #append>
              <el-button
                :disabled="sending || countdown > 0"
                @click="handleSendCode"
              >
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleRegister"
          >
            注册
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  phone: '',
  code: '',
})

const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)

let timer = null

const PHONE_REGEX = /^1[3-9]\d{9}$/

function validatePhone() {
  if (!form.phone) {
    ElMessage.warning('请输入手机号')
    return false
  }
  if (!PHONE_REGEX.test(form.phone)) {
    ElMessage.error('手机号格式不正确，请输入中国大陆手机号')
    return false
  }
  return true
}

function startCountdown() {
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

async function handleSendCode() {
  if (!validatePhone()) {
    return
  }
  sending.value = true
  try {
    await authApi.sendCode(form.phone)
    form.code = '8888'
    ElMessage.success('验证码已发送')
    startCountdown()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '发送验证码失败')
  } finally {
    sending.value = false
  }
}

async function handleAuth(action) {
  if (!validatePhone()) {
    return
  }
  if (!form.code) {
    ElMessage.warning('请输入验证码')
    return
  }
  loading.value = true
  try {
    const { data } = await action(form.phone, form.code)
    authStore.setAuth(data.token, data.phone)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  } finally {
    loading.value = false
  }
}

function handleLogin() {
  handleAuth(authApi.login)
}

function handleRegister() {
  handleAuth(authApi.register)
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.login-card {
  width: 420px;
}

.login-title {
  text-align: center;
  font-size: 20px;
  font-weight: 500;
  margin: 0;
}

.login-btn {
  width: 100%;
}
</style>

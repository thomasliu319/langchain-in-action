<template>
  <div class="login-container">
    <div class="login-form">
      <h1 class="login-title">X智能医疗助手</h1>
      <h2 class="login-subtitle">登录</h2>

      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-button" @click="handleLogin" :loading="loading">
            登录
          </el-button>
          <el-button type="default" class="register-button" @click="goToRegister">
            注册
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import axios from 'axios';

const router = useRouter();
const loginFormRef = ref();
const loading = ref(false);

const loginForm = reactive({
  username: '',
  password: ''
});

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;

  try {
    await loginFormRef.value.validate();
    loading.value = true;

    const response = await axios.post('http://localhost:8005/auth/token', new URLSearchParams({
      username: loginForm.username,
      password: loginForm.password
    }), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });

    // 保存 token
    localStorage.setItem('token', response.data.access_token);

    // 保存用户信息（从登录响应中获取）
    localStorage.setItem('user', JSON.stringify({
      id: response.data.user_id,
      username: loginForm.username
    }));

    ElMessage.success('登录成功');
    router.push('/');
  } catch (error) {
    if (error.response) {
      ElMessage.error(error.response.data.detail || '登录失败');
    } else {
      ElMessage.error('网络错误，请稍后再试');
    }
  } finally {
    loading.value = false;
  }
};

const goToRegister = () => {
  router.push('/register');
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
  padding: 20px;
}

.login-form {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  width: 100%;
  max-width: 400px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  margin-bottom: 8px;
}

.login-subtitle {
  font-size: 18px;
  color: #a0aec0;
  text-align: center;
  margin-bottom: 32px;
}

.login-button {
  width: 100%;
  margin-bottom: 16px;
  background: linear-gradient(90deg, #3182ce, #4299e1);
  border: none;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
}

.register-button {
  width: 100%;
  background: transparent;
  border: 1px solid #4299e1;
  color: #4299e1;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  margin: 0 auto 0 0;
}

.el-input__wrapper {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

.el-input__inner {
  color: #fff;
}

.el-input__placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.el-form-item__label {
  color: #a0aec0;
}

.el-form-item.is-error .el-input__wrapper {
  border-color: #f56565;
}

.el-form-item__error {
  color: #f56565;
}
</style>

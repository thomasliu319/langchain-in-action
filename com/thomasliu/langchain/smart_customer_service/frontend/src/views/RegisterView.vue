<template>
  <div class="register-container">
    <div class="register-form">
      <h1 class="register-title">小滴智能医疗助手</h1>
      <h2 class="register-subtitle">注册</h2>

      <el-form :model="registerForm" :rules="rules" ref="registerFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="register-button" @click="handleRegister" :loading="loading">
            注册
          </el-button>
          <el-button type="default" class="login-button" @click="goToLogin">
            登录
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
const registerFormRef = ref();
const loading = ref(false);

const registerForm = reactive({
  username: '',
  password: '',
  email: ''
});

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
};

const handleRegister = async () => {
  if (!registerFormRef.value) return;

  try {
    await registerFormRef.value.validate();
    loading.value = true;

    const response = await axios.post('http://localhost:8005/auth/register', {
      username: registerForm.username,
      password: registerForm.password,
      email: registerForm.email
    });

    ElMessage.success('注册成功，请登录');
    router.push('/login');
  } catch (error) {
    if (error.response) {
      ElMessage.error(error.response.data.detail || '注册失败');
    } else {
      ElMessage.error('网络错误，请稍后再试');
    }
  } finally {
    loading.value = false;
  }
};

const goToLogin = () => {
  router.push('/login');
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
  padding: 20px;
}

.register-form {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  width: 100%;
  max-width: 400px;
}

.register-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  margin-bottom: 8px;
}

.register-subtitle {
  font-size: 18px;
  color: #a0aec0;
  text-align: center;
  margin-bottom: 32px;
}

.register-button {
  width: 100%;
  margin-bottom: 16px;
  background: linear-gradient(90deg, #3182ce, #4299e1);
  border: none;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
}

.login-button {
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

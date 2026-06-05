<template>
  <div class="langchain-style">
    <header class="langchain-header">
      <div class="header-content">
        <div class="logo">
          <span class="logo-text">X智能医疗助手</span>
        </div>
        <div class="nav">
          <router-link to="/" class="nav-link">首页</router-link>
          <router-link to="/preferences" class="nav-link active">偏好设置</router-link>
          <router-link to="/about" class="nav-link">关于</router-link>
        </div>
        <div class="user-info">
          <span class="user-id">{{ userId }}</span>
        </div>
      </div>
    </header>

    <main class="preferences-container">
      <section class="hero-section">
        <div class="hero-content">
          <h1 class="hero-title">医疗偏好设置</h1>
          <p class="hero-subtitle">自定义您的智能医疗助手体验</p>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-content">
          <div class="settings-card">
            <h2 class="card-title">回答风格</h2>
            <div class="setting-item">
              <div class="setting-label">
                <el-icon :size="20"><ChatDotRound /></el-icon>
                <span>偏好的回答风格</span>
              </div>
              <div class="setting-control">
                <el-select
                  v-model="preferredStyle"
                  placeholder="选择回答风格"
                  class="style-select"
                >
                  <el-option label="简洁" value="简洁" />
                  <el-option label="详细" value="详细" />
                  <el-option label="专业" value="专业" />
                  <el-option label="友好" value="友好" />
                </el-select>
                <el-button
                  class="langchain-button primary"
                  @click="saveStyle"
                >
                  保存
                </el-button>
              </div>
            </div>
          </div>

          <div class="settings-card">
            <h2 class="card-title">医疗信息</h2>
            <div class="setting-item">
              <div class="setting-label">
                <el-icon :size="20"><User /></el-icon>
                <span>过敏史</span>
              </div>
              <div class="setting-control">
                <el-input
                  v-model="allergies"
                  placeholder="请输入您的过敏史"
                  class="address-input"
                />
                <el-button
                  class="langchain-button primary"
                  @click="saveAllergies"
                >
                  保存
                </el-button>
              </div>
            </div>
          </div>

          <div class="settings-card">
            <h2 class="card-title">用户信息</h2>
            <div class="setting-item">
              <div class="setting-label">
                <el-icon :size="20"><User /></el-icon>
                <span>用户 ID</span>
              </div>
              <div class="setting-value">
                <span class="user-id-display">{{ userId }}</span>
                <el-button
                  class="langchain-button secondary"
                  @click="generateNewUserId"
                >
                  生成新 ID
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <footer class="langchain-footer">
      <div class="footer-content">
        <div class="footer-links">
          <a href="/" class="footer-link">首页</a>
          <a href="/preferences" class="footer-link">偏好设置</a>
          <a href="/about" class="footer-link">关于</a>
        </div>
        <div class="footer-copyright">
          © 2026 智能医疗助手 | 基于 LangChain 构建
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const userId = ref('user_' + Math.random().toString(36).substr(2, 9))
const preferredStyle = ref('')
const allergies = ref('')
const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8005'

// 检查登录状态
const checkLoginStatus = () => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
  }
}

const loadPreferences = async () => {
  try {
    const response = await axios.get(`${backendUrl}/preferences/list`, {
      params: { user_id: userId.value },
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    const prefs = response.data.preferences
    // 解析偏好设置
    if (prefs) {
      const prefLines = prefs.split('\n')
      prefLines.forEach(line => {
        const [key, value] = line.split(': ')
        if (key === 'preferred_style') {
          preferredStyle.value = value
        } else if (key === 'allergies') {
          allergies.value = value
        }
      })
    }
  } catch (error) {
    console.error('加载偏好失败:', error)
  }
}

const saveStyle = async () => {
  try {
    await axios.post(`${backendUrl}/preferences/save`, {
      user_id: userId.value,
      key: 'preferred_style',
      value: preferredStyle.value
    }, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    ElMessage.success(`偏好已保存: ${preferredStyle.value}`)
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

const saveAllergies = async () => {
  try {
    await axios.post(`${backendUrl}/preferences/save`, {
      user_id: userId.value,
      key: 'allergies',
      value: allergies.value
    }, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    ElMessage.success('过敏史已保存')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

const generateNewUserId = () => {
  userId.value = 'user_' + Math.random().toString(36).substr(2, 9)
  ElMessage.info('已生成新的用户 ID')
  loadPreferences()
}

onMounted(() => {
  checkLoginStatus()
  loadPreferences()
})
</script>

<style scoped>
.langchain-style {
  min-height: 100vh;
  background: #0a0a0f;
  color: #ffffff;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.langchain-header {
  background: rgba(10, 10, 15, 0.95);
  border-bottom: 1px solid rgba(50, 200, 255, 0.2);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #32c8ff 0%, #1e90ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-fill-color: transparent;
}

.nav {
  display: flex;
  gap: 30px;
}

.nav-link {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  position: relative;
}

.nav-link:hover {
  color: #32c8ff;
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(135deg, #32c8ff 0%, #1e90ff 100%);
  border-radius: 1px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-id {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  padding: 6px 12px;
  background: rgba(50, 200, 255, 0.1);
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-radius: 16px;
}

.preferences-container {
  min-height: 80vh;
}

.hero-section {
  background: linear-gradient(135deg, rgba(50, 200, 255, 0.1) 0%, rgba(30, 144, 255, 0.1) 100%);
  padding: 60px 20px;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(50, 200, 255, 0.1)" stroke-width="0.5"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
  opacity: 0.3;
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.hero-title {
  font-size: 36px;
  font-weight: 700;
  background: linear-gradient(135deg, #32c8ff 0%, #1e90ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-fill-color: transparent;
  margin: 0;
}

.hero-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
  line-height: 1.6;
}

.settings-section {
  padding: 60px 20px;
  background: rgba(10, 10, 15, 0.8);
}

.section-content {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.settings-card {
  background: rgba(25, 25, 40, 0.8);
  border: 1px solid rgba(50, 200, 255, 0.1);
  border-radius: 12px;
  padding: 30px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.settings-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(50, 200, 255, 0.05) 0%, rgba(30, 144, 255, 0.05) 100%);
  z-index: 0;
}

.settings-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(50, 200, 255, 0.15);
  border-color: rgba(50, 200, 255, 0.2);
}

.card-title {
  position: relative;
  z-index: 1;
  font-size: 18px;
  font-weight: 600;
  color: #32c8ff;
  margin: 0 0 20px 0;
  border-bottom: 1px solid rgba(50, 200, 255, 0.2);
  padding-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.setting-item {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
}

.setting-control {
  display: flex;
  gap: 12px;
  align-items: center;
}

.setting-value {
  display: flex;
  gap: 12px;
  align-items: center;
}

.style-select {
  flex: 1;
  width: 100%;
}

.address-input {
  flex: 1;
  width: 100%;
}

.user-id-display {
  font-size: 14px;
  font-family: 'Courier New', monospace;
  color: rgba(255, 255, 255, 0.8);
  background: rgba(50, 200, 255, 0.1);
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-radius: 8px;
  padding: 8px 16px;
  flex: 1;
  word-break: break-all;
}

.langchain-button {
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  padding: 10px 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.langchain-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.6s ease;
}

.langchain-button:hover::before {
  left: 100%;
}

.langchain-button.primary {
  background: linear-gradient(135deg, #32c8ff 0%, #1e90ff 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(50, 200, 255, 0.3);
}

.langchain-button.primary:hover {
  box-shadow: 0 6px 20px rgba(50, 200, 255, 0.4);
  transform: translateY(-1px);
}

.langchain-button.secondary {
  background: rgba(50, 200, 255, 0.1);
  color: #32c8ff;
  border: 1px solid rgba(50, 200, 255, 0.3);
  box-shadow: 0 2px 8px rgba(50, 200, 255, 0.15);
}

.langchain-button.secondary:hover {
  background: rgba(50, 200, 255, 0.15);
  box-shadow: 0 4px 12px rgba(50, 200, 255, 0.25);
  transform: translateY(-1px);
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-select__wrapper) {
  background: rgba(25, 25, 40, 0.8) !important;
  border: 1px solid rgba(50, 200, 255, 0.2) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}

:deep(.el-select__placeholder) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.el-select__input) {
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.el-select__caret) {
  color: rgba(50, 200, 255, 0.6) !important;
}

:deep(.el-select-dropdown) {
  background: rgba(25, 25, 40, 0.95) !important;
  border: 1px solid rgba(50, 200, 255, 0.2) !important;
  border-radius: 8px !important;
  backdrop-filter: blur(10px);
}

:deep(.el-select-dropdown__item) {
  color: rgba(255, 255, 255, 0.8) !important;
  padding: 10px 20px !important;
  transition: all 0.3s ease !important;
}

:deep(.el-select-dropdown__item:hover) {
  background: rgba(50, 200, 255, 0.1) !important;
  color: #32c8ff !important;
}

:deep(.el-select-dropdown__item.selected) {
  background: rgba(50, 200, 255, 0.15) !important;
  color: #32c8ff !important;
}

:deep(.el-input__wrapper) {
  background: rgba(25, 25, 40, 0.8) !important;
  border: 1px solid rgba(50, 200, 255, 0.2) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}

:deep(.el-input__inner) {
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.el-input__placeholder) {
  color: rgba(255, 255, 255, 0.4) !important;
}

:deep(.el-input__inner:focus) {
  border-color: #32c8ff !important;
  box-shadow: 0 0 0 2px rgba(50, 200, 255, 0.2) !important;
}

.langchain-footer {
  background: rgba(10, 10, 15, 0.95);
  border-top: 1px solid rgba(50, 200, 255, 0.2);
  backdrop-filter: blur(10px);
  margin-top: 60px;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 30px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.footer-links {
  display: flex;
  gap: 30px;
  justify-content: center;
}

.footer-link {
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.3s ease;
}

.footer-link:hover {
  color: #32c8ff;
}

.footer-copyright {
  text-align: center;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }

  .nav {
    flex-wrap: wrap;
    justify-content: center;
  }

  .hero-title {
    font-size: 28px;
  }

  .hero-subtitle {
    font-size: 14px;
  }

  .settings-section {
    padding: 40px 20px;
  }

  .settings-card {
    padding: 20px;
  }

  .setting-control {
    flex-direction: column;
    align-items: stretch;
  }

  .setting-value {
    flex-direction: column;
    align-items: stretch;
  }

  .user-id-display {
    text-align: center;
  }
}
</style>

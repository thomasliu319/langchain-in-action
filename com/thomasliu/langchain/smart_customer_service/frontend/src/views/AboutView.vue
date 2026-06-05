<template>
  <div class="langchain-style">
    <header class="langchain-header">
      <div class="header-content">
        <div class="logo">
          <span class="logo-text">X智能医疗助手</span>
        </div>
        <div class="nav">
          <router-link to="/" class="nav-link">首页</router-link>
          <router-link to="/preferences" class="nav-link">偏好设置</router-link>
          <router-link to="/about" class="nav-link active">关于</router-link>
        </div>
        <div class="user-info">
          <span class="user-id" v-if="user">{{ user.username }}</span>
        </div>
      </div>
    </header>

    <main class="about-container">
      <section class="hero-section">
        <div class="hero-content">
          <h1 class="hero-title">X智能医疗助手</h1>
          <p class="hero-subtitle">基于 LangChain 1.x 构建的先进人工智能医疗咨询解决方案</p>
          <div class="hero-buttons">
            <a href="/" class="langchain-button primary">开始咨询</a>
            <a href="#features" class="langchain-button secondary">了解更多</a>
          </div>
        </div>
      </section>

      <section id="features" class="features-section">
        <div class="section-content">
          <h2 class="section-title">核心功能</h2>
          <div class="features-grid">
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="24"><Document /></el-icon>
              </div>
              <h3 class="feature-title">RAG 技术</h3>
              <p class="feature-description">基于医疗文档的智能检索问答，提供准确的医疗信息</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="24"><Clock /></el-icon>
              </div>
              <h3 class="feature-title">长记忆</h3>
              <p class="feature-description">用户偏好和医疗历史持久化，提供个性化医疗服务</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="24"><Message /></el-icon>
              </div>
              <h3 class="feature-title">短记忆</h3>
              <p class="feature-description">当前会话上下文保持，实现连贯的医疗咨询体验</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="24"><Link /></el-icon>
              </div>
              <h3 class="feature-title">MCP 协议</h3>
              <p class="feature-description">标准化工具调用协议，实现模块化医疗功能扩展</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="24"><Grid /></el-icon>
              </div>
              <h3 class="feature-title">多智能体协作</h3>
              <p class="feature-description">私人医疗顾问、主治医生、体检员、药师多角色协同</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">
                <el-icon :size="24"><User /></el-icon>
              </div>
              <h3 class="feature-title">个性化服务</h3>
              <p class="feature-description">根据用户情况提供定制化医疗建议和治疗方案</p>
            </div>
          </div>
        </div>
      </section>

      <section class="tech-stack-section">
        <div class="section-content">
          <h2 class="section-title">技术栈</h2>
          <div class="tech-grid">
            <div class="tech-card">
              <h3 class="tech-title">后端</h3>
              <ul class="tech-list">
                <li>Python 3.12+</li>
                <li>LangChain 1.0.3</li>
                <li>FastAPI</li>
                <li>LangGraph</li>
                <li>ChromaDB</li>
                <li>DashScope Embeddings</li>
              </ul>
            </div>
            <div class="tech-card">
              <h3 class="tech-title">前端</h3>
              <ul class="tech-list">
                <li>Vue 3</li>
                <li>TypeScript</li>
                <li>Element Plus</li>
                <li>Vite</li>
                <li>Pinia</li>
                <li>Vue Router</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section class="architecture-section">
        <div class="section-content">
          <h2 class="section-title">系统架构</h2>
          <div class="architecture-diagram">
            <div class="architecture-layer">
              <div class="layer-title">接入层</div>
              <div class="layer-content">FastAPI REST API</div>
            </div>
            <div class="architecture-layer">
              <div class="layer-title">智能体层</div>
              <div class="layer-content">
                <div>• 私人医疗顾问</div>
                <div>• 主治医生</div>
                <div>• 体检员</div>
                <div>• 药师</div>
              </div>
            </div>
            <div class="architecture-layer">
              <div class="layer-title">工具层</div>
              <div class="layer-content">
                <div>• RAG 医疗文档检索</div>
                <div>• 联网搜索</div>
                <div>• MCP 工具</div>
              </div>
            </div>
            <div class="architecture-layer">
              <div class="layer-title">记忆层</div>
              <div class="layer-content">
                <div>• MySQL (持久化存储)</div>
                <div>• Chroma (医疗文档向量存储)</div>
                <div>• SQLite (短记忆)</div>
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
          © 2026 X智能医疗助手 | 基于 LangChain 构建
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const user = ref<any>(null)

// 检查登录状态
const checkLoginStatus = () => {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  if (!token) {
    router.push('/login')
  } else if (userStr) {
    user.value = JSON.parse(userStr)
  }
}

onMounted(() => {
  checkLoginStatus()
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
  margin-right: 10px;
}

.about-container {
  min-height: 80vh;
}

.hero-section {
  background: linear-gradient(135deg, rgba(50, 200, 255, 0.1) 0%, rgba(30, 144, 255, 0.1) 100%);
  padding: 100px 20px;
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
  gap: 20px;
  align-items: center;
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  background: linear-gradient(135deg, #32c8ff 0%, #1e90ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-fill-color: transparent;
  margin: 0;
}

.hero-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
  line-height: 1.6;
}

.hero-buttons {
  display: flex;
  gap: 15px;
  margin-top: 20px;
}

.features-section {
  padding: 80px 20px;
  background: rgba(15, 15, 25, 0.5);
}

.section-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.section-title {
  font-size: 32px;
  font-weight: 700;
  color: #ffffff;
  text-align: center;
  margin: 0;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 3px;
  background: linear-gradient(135deg, #32c8ff 0%, #1e90ff 100%);
  border-radius: 2px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.feature-card {
  background: rgba(25, 25, 40, 0.8);
  border: 1px solid rgba(50, 200, 255, 0.1);
  border-radius: 12px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(50, 200, 255, 0.05) 0%, rgba(30, 144, 255, 0.05) 100%);
  z-index: 0;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(50, 200, 255, 0.2);
  border-color: rgba(50, 200, 255, 0.3);
}

.feature-icon {
  position: relative;
  z-index: 1;
  width: 60px;
  height: 60px;
  background: rgba(50, 200, 255, 0.1);
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #32c8ff;
}

.feature-title {
  position: relative;
  z-index: 1;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.feature-description {
  position: relative;
  z-index: 1;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  margin: 0;
}

.tech-stack-section {
  padding: 80px 20px;
  background: rgba(10, 10, 15, 0.8);
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.tech-card {
  background: rgba(25, 25, 40, 0.8);
  border: 1px solid rgba(50, 200, 255, 0.1);
  border-radius: 12px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  transition: all 0.3s ease;
}

.tech-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(50, 200, 255, 0.15);
  border-color: rgba(50, 200, 255, 0.2);
}

.tech-title {
  font-size: 18px;
  font-weight: 600;
  color: #32c8ff;
  margin: 0;
  border-bottom: 1px solid rgba(50, 200, 255, 0.2);
  padding-bottom: 10px;
}

.tech-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tech-list li {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  padding-left: 20px;
  position: relative;
}

.tech-list li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #32c8ff;
  font-weight: bold;
}

.architecture-section {
  padding: 80px 20px;
  background: rgba(15, 15, 25, 0.5);
}

.architecture-diagram {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.architecture-layer {
  background: rgba(25, 25, 40, 0.8);
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.architecture-layer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(50, 200, 255, 0.05) 0%, rgba(30, 144, 255, 0.05) 100%);
  z-index: 0;
}

.architecture-layer:hover {
  transform: translateX(5px);
  box-shadow: 0 4px 15px rgba(50, 200, 255, 0.2);
  border-color: rgba(50, 200, 255, 0.3);
}

.layer-title {
  position: relative;
  z-index: 1;
  font-size: 16px;
  font-weight: 600;
  color: #32c8ff;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.layer-content {
  position: relative;
  z-index: 1;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

.layer-content div {
  margin: 5px 0;
}

.langchain-button {
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  padding: 12px 24px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
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
    font-size: 36px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .hero-buttons {
    flex-direction: column;
    width: 100%;
    max-width: 300px;
  }

  .features-grid,
  .tech-grid {
    grid-template-columns: 1fr;
  }

  .section-content {
    padding: 0 10px;
  }

  .features-section,
  .tech-stack-section,
  .architecture-section {
    padding: 60px 20px;
  }
}
</style>

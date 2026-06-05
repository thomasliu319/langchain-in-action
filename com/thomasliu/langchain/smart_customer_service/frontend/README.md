# X智能医疗助手 - 前端

基于 Vue 3 + TypeScript + Element Plus 的医疗助手前端应用

## 项目概述

X智能医疗助手前端是一个现代化的单页应用（SPA），提供用户友好的医疗咨询界面，支持多智能体对话、医疗文档上传、会话管理等功能。

## 技术栈

- **Vue 3**: 渐进式 JavaScript 框架（Composition API）
- **TypeScript**: 类型安全的 JavaScript 超集
- **Element Plus**: Vue 3 组件库
- **Vite**: 现代化构建工具
- **Vue Router**: 路由管理
- **Axios**: HTTP 客户端
- **Marked.js**: Markdown 渲染库

## 项目结构

```
frontend/smart-customer-service/
├── public/
│   └── favicon.ico              # 网站图标
│
├── src/
│   ├── assets/                  # 静态资源
│   │   ├── base.css             # 基础样式
│   │   ├── main.css             # 主样式
│   │   └── logo.svg             # Logo
│   │
│   ├── components/              # 可复用组件
│   │   └── icons/               # 图标组件
│   │
│   ├── router/                  # 路由配置
│   │   └── index.ts             # 路由定义
│   │
│   ├── views/                   # 页面组件
│   │   ├── HomeView.vue         # 聊天主页面
│   │   ├── LoginView.vue        # 登录页面
│   │   ├── RegisterView.vue     # 注册页面
│   │   ├── AboutView.vue        # 关于页面
│   │   └── PreferencesView.vue  # 偏好设置页面
│   │
│   ├── App.vue                  # 根组件
│   └── main.ts                  # 应用入口
│
├── .env                         # 环境变量
├── .env.example                 # 环境变量示例
├── vite.config.ts               # Vite 配置
├── tsconfig.json                # TypeScript 配置
├── package.json                 # 依赖管理
└── README.md                    # 前端文档
```

## 安装步骤

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制示例文件并编辑：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
# 后端 API 地址
VITE_BACKEND_URL=http://localhost:8005
```

### 3. 运行开发服务器

```bash
npm run dev
```

前端将在 http://localhost:5173 启动

### 4. 构建生产版本

```bash
npm run build
```

构建产物将生成在 `dist/` 目录

## 功能特性

### 核心功能

- ✅ **用户认证** - 登录、注册、Token 管理
- ✅ **实时聊天** - 与多智能体医疗助手对话
- ✅ **Markdown 渲染** - 支持 Markdown 格式消息展示
- ✅ **会话管理** - 会话列表、历史消息、会话切换
- ✅ **医疗文档上传** - PDF 文档上传，居中弹窗提示
- ✅ **偏好设置** - 个性化服务配置
- ✅ **响应式设计** - 支持桌面和移动端

### 页面说明

#### 1. 登录页面（LoginView）

**功能**：
- 用户名/密码登录表单
- 跳转到注册页面链接
- 登录成功后保存 Token 和用户 ID 到 localStorage
- 自动跳转到聊天页面

**布局**：
- 居中的登录卡片
- 项目标题"X智能医疗助手"
- 简洁现代的 UI 设计

#### 2. 注册页面（RegisterView）

**功能**：
- 新用户注册表单
- 用户名、密码、邮箱验证
- 注册成功后跳转到登录页面

#### 3. 聊天主页面（HomeView）

**布局结构**：

**顶部导航栏**：
- 左侧：项目标题"X智能医疗助手"
- 右侧：用户名显示、登出按钮

**左侧会话列表**：
- 固定高度，内部滚动
- 显示所有历史会话
- "＋新会话"按钮
- 点击会话加载历史消息
- 当前会话高亮显示

**右侧聊天区域**：
- **消息展示区**：
  - 固定高度，内部滚动
  - 用户消息：右侧显示，蓝色气泡
  - AI 消息：左侧显示，深色背景
  - 支持 Markdown 渲染
  - 每条消息显示时间戳
  
- **输入区域**：
  - 文本输入框（支持 Shift+Enter 换行）
  - Enter 发送消息
  - "上传医疗文档"按钮
  - "发送"按钮

**文档上传弹窗**：
- 居中显示，半透明黑色遮罩
- 紫色渐变背景（#667eea → #764ba2）
- 白色文字
- 上传图标（带跳动动画）
- 蓝绿色渐变进度条
- 持续到文档上传、解析、AI 分析完成
- 完成后自动关闭并显示成功提示

#### 4. 关于页面（AboutView）

**内容**：
- 系统介绍
- 核心功能说明
- 技术栈展示
- 系统架构图

#### 5. 偏好设置页面（PreferencesView）

**功能**：
- 查看和编辑用户偏好
- 沟通风格设置
- 收货地址管理
- 用户 ID 显示

## 核心功能实现

### 1. 用户认证

**登录流程**：
```typescript
// 1. 调用后端登录接口
const response = await axios.post(`${backendUrl}/auth/token`, {
  username: form.username,
  password: form.password
})

// 2. 保存 Token 和用户 ID
localStorage.setItem('token', response.data.access_token)
localStorage.setItem('user_id', response.data.user_id.toString())

// 3. 跳转到聊天页面
router.push('/')
```

**Token 管理**：
- 登录成功后保存到 localStorage
- 后续请求在 Header 中携带 Token
- 登出时清除 Token

### 2. 聊天功能

**发送消息**：
```typescript
const handleSend = async () => {
  if (!inputMessage.value.trim()) return
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date()
  })
  
  // 调用后端 API
  const response = await axios.post(`${backendUrl}/chat/send`, {
    user_id: userId.value,
    message: inputMessage.value,
    conversation_id: currentConversationId.value
  })
  
  // 添加 AI 回复
  messages.value.push({
    role: 'assistant',
    content: response.data.reply,
    timestamp: new Date()
  })
  
  scrollToBottom()
}
```

**Markdown 渲染**：
```vue
<div v-html="renderContent(message.content)" class="message-content"></div>
```

```typescript
import { marked } from 'marked'

const renderContent = (content: string) => {
  return marked(content)
}
```

### 3. 会话管理

**加载会话列表**：
```typescript
const loadConversations = async () => {
  const response = await axios.get(`${backendUrl}/conversations/list`, {
    params: { user_id: userId.value }
  })
  conversations.value = response.data
}
```

**切换会话**：
```typescript
const selectConversation = async (conv: Conversation) => {
  currentConversationId.value = conv.id
  await loadMessages(conv.id)
}
```

**创建新会话**：
```typescript
const createNewConversation = async () => {
  const response = await axios.post(`${backendUrl}/conversations/create`, {
    user_id: userId.value,
    title: '新会话'
  })
  currentConversationId.value = response.data.id
  messages.value = []
  await loadConversations()
}
```

### 4. 医疗文档上传

**上传流程**：
```typescript
const handleFileUpload = async (file: any) => {
  // 1. 询问文档类型
  const documentType = prompt('请选择文档类型:', '病历本')
  if (!documentType) return
  
  // 2. 显示上传状态
  isUploading.value = true
  uploadProgress.value = 0
  
  // 3. 模拟进度条动画
  const progressInterval = setInterval(() => {
    if (uploadProgress.value < 90) {
      uploadProgress.value += Math.random() * 15
    }
  }, 500)
  
  // 4. 上传文件
  const formData = new FormData()
  formData.append('file', file.raw)
  formData.append('document_type', documentType)
  formData.append('user_id', userId.value)
  
  const response = await axios.post(`${backendUrl}/documents/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'Authorization': `Bearer ${token}`
    }
  })
  
  // 5. 上传完成
  clearInterval(progressInterval)
  uploadProgress.value = 100
  
  // 6. 自动发送消息给 AI
  const userMessage = `我上传了一份医疗文档：${file.name}`
  messages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  })
  
  // 7. 调用 AI 分析
  await processDocumentWithAI(file.name, documentType)
  
  // 8. 关闭上传状态
  setTimeout(() => {
    isUploading.value = false
    uploadProgress.value = 0
  }, 500)
}
```

**文档上传弹窗**：
```vue
<transition name="upload-fade">
  <div v-if="isUploading" class="upload-overlay">
    <div class="upload-dialog">
      <div class="upload-icon">
        <el-icon class="is-loading" :size="48"><Upload /></el-icon>
      </div>
      <div class="upload-text">
        <h3>正在上传并分析文档...</h3>
        <p>请稍候，系统正在提取医疗信息</p>
      </div>
      <div class="upload-progress">
        <el-progress :percentage="uploadProgress" :stroke-width="8" :show-text="false" />
      </div>
    </div>
  </div>
</transition>
```

### 5. Markdown 样式优化

**CSS 样式**：
```css
.message-content {
  line-height: 1.6;
}

.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3) {
  margin: 0.5em 0;
}

.message-content :deep(p) {
  margin: 0.5em 0;
}

.message-content :deep(p:empty) {
  display: none;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.message-content :deep(li) {
  margin: 0.3em 0;
}
```

## 环境变量

在 `.env` 文件中配置后端 API 地址：

```env
# 开发环境
VITE_BACKEND_URL=http://localhost:8005

# 生产环境
VITE_BACKEND_URL=https://api.example.com
```

## 路由配置

```typescript
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView
    },
    {
      path: '/about',
      name: 'about',
      component: AboutView
    },
    {
      path: '/preferences',
      name: 'preferences',
      component: PreferencesView,
      meta: { requiresAuth: true }
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})
```

## 响应式设计

**断点**：
- 桌面端：> 768px
- 移动端：<= 768px

**移动端适配**：
```css
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
  
  .chat-container {
    padding: 20px 15px;
  }
  
  .messages-container,
  .input-section {
    padding: 20px;
  }
  
  .message {
    max-width: 90%;
  }
}
```

## 开发规范

### 代码规范

- 使用 Vue 3 Composition API
- TypeScript 类型安全
- 组件命名使用 PascalCase
- 文件名使用 kebab-case

### 样式规范

- 使用 scoped 样式
- 避免全局样式污染
- 使用 CSS 变量管理主题色

### 组件规范

- 单一职责原则
-  props 类型验证
-  事件命名使用 kebab-case

## 构建和部署

### 开发环境

```bash
npm run dev
```

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录

### 部署

**Nginx 配置**：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/smart-customer-service/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://localhost:8005/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 故障排查

### 常见问题

1. **前端无法连接后端**
   - 检查 `.env` 中的 `VITE_BACKEND_URL`
   - 确认后端服务是否运行
   - 查看浏览器控制台错误

2. **Markdown 渲染问题**
   - 确保安装了 `marked` 库
   - 检查 CSS 样式是否影响渲染
   - 确认后端返回的内容格式正确

3. **文档上传失败**
   - 检查文件大小限制
   - 确认后端 uploads 目录权限
   - 查看网络请求错误

4. **会话列表为空**
   - 检查 user_id 是否正确
   - 确认数据库连接正常
   - 查看后端日志

## 扩展功能

### 可扩展方向

1. **多语言支持**
   - 使用 vue-i18n 实现国际化
   - 支持中文、英文切换

2. **主题切换**
   - 支持亮色/暗色主题
   - 自定义主题色

3. **消息搜索**
   - 在会话中搜索关键词
   - 高亮显示搜索结果

4. **消息收藏**
   - 收藏重要消息
   - 查看收藏列表

5. **语音输入**
   - 语音转文字
   - 语音消息发送

## 许可证

MIT License

---

**版本**：v2.0  
**更新日期**：2026-04-14

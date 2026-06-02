<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElUpload, ElButton, ElIcon, ElPopconfirm } from 'element-plus'
import { Upload, Document, Message as MessageIcon, Close, Plus, Delete } from '@element-plus/icons-vue'
import { marked } from 'marked'
import axios from 'axios'
import { useRouter } from 'vue-router'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface Conversation {
  id: string
  title: string
  lastMessage: string
  lastActive: Date
  messages: Message[]
}

const router = useRouter()
const messages = ref<Message[]>([])
const inputMessage = ref('')
const userId = ref('')  // 使用登录用户的真实ID，不再随机生成
const threadId = ref('')

// 打字机效果相关
const isTyping = ref(false)
const currentAiContent = ref('')
const typingTimer = ref<number | null>(null)
const pendingContent = ref('')

const messagesContainerRef = ref<HTMLElement | null>(null)
const user = ref<any>(null)
const uploadedFiles = ref<any[]>([])
const isUploading = ref(false)  // 文档上传状态
const uploadProgress = ref(0)  // 上传进度

// 会话列表
const conversations = ref<Conversation[]>([])
const currentConversation = ref<string>('')

const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8005'

// 检查登录状态
const checkLoginStatus = () => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    user.value = JSON.parse(userStr)
    // 使用登录用户的真实ID作为长记忆的user_id
    userId.value = 'user_' + user.value.id
  } else {
    router.push('/login')
  }
}

// 加载会话列表
const loadConversations = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`${backendUrl}/conversations/list`, {
      params: {
        user_id: user.value.id
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 200) {
      const convs = response.data.conversations
      conversations.value = convs.map((conv: any) => ({
        ...conv,
        lastActive: new Date(conv.lastActive),
        created_at: new Date(conv.created_at),
        messages: []
      }))

      // 如果有会话，加载第一个会话
      if (conversations.value.length > 0) {
        await selectConversation(conversations.value[0].id)
      } else {
        await createNewConversation()
      }
    }
  } catch (error) {
    console.error('加载会话列表失败:', error)
    // 如果加载失败，创建一个新会话
    await createNewConversation()
  }
}

// 创建新会话
const createNewConversation = async () => {
  try {
    // 检查用户是否已登录
    if (!user.value || !user.value.id) {
      ElMessage.error('用户未登录，请重新登录')
      router.push('/login')
      return
    }

    const newId = 'conv_' + Math.random().toString(36).substr(2, 9)
    const token = localStorage.getItem('token')

    // 调用后端API创建会话
    const response = await axios.post(`${backendUrl}/conversations/create`, {
      id: newId,
      title: newId
    }, {
      params: {
        user_id: user.value.id
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 200) {
      const newConv = response.data.conversation
      const conversation: Conversation = {
        id: newConv.id,
        title: newConv.title,
        lastMessage: newConv.last_message,
        lastActive: new Date(newConv.last_active),
        messages: [{
          role: 'assistant',
          content: '您好！我是小滴智能医疗助手，请问有什么可以帮您？',
          timestamp: new Date()
        }]
      }

      conversations.value.unshift(conversation)
      await selectConversation(newId)

      // AI欢迎消息由前端展示，后端自动处理持久化
      // 无需前端调用 save_message 接口
    }
  } catch (error) {
    console.error('创建会话失败:', error)
    ElMessage.error('创建会话失败，请重试')
  }
}

// 选择会话
const selectConversation = async (convId: string) => {
  try {
    currentConversation.value = convId
    const token = localStorage.getItem('token')

    // 调用后端API获取会话详情和消息
    const response = await axios.get(`${backendUrl}/conversations/get`, {
      params: {
        conversation_id: convId
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 200) {
      console.log('获取会话详情响应:', response.data)
      const messagesData = response.data.messages || []
      console.log('消息数据:', messagesData)

      messages.value = messagesData.map((msg) => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date()
      }))

      console.log('处理后的消息:', messages.value)

      // 如果消息列表为空，添加AI的欢迎消息
      if (messages.value.length === 0) {
        const welcomeMessage = '您好！我是小滴智能医疗助手，请问有什么可以帮您？'
        messages.value.push({
          role: 'assistant',
          content: welcomeMessage,
          timestamp: new Date()
        })
      }

      threadId.value = convId
      scrollToBottom()
    }
  } catch (error) {
    console.error('获取会话详情失败:', error)
    ElMessage.error('获取会话详情失败，请重试')
  }
}

// 删除会话
const deleteConversation = async (convId: string) => {
  try {
    const token = localStorage.getItem('token')

    // 调用后端API删除会话
    const response = await axios.delete(`${backendUrl}/conversations/delete`, {
      params: {
        conversation_id: convId
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 200) {
      const index = conversations.value.findIndex(conv => conv.id === convId)
      if (index !== -1) {
        conversations.value.splice(index, 1)

        // 如果删除的是当前会话，选择第一个会话或创建新会话
        if (currentConversation.value === convId) {
          if (conversations.value.length > 0) {
            await selectConversation(conversations.value[0].id)
          } else {
            await createNewConversation()
          }
        }
      }
    }
  } catch (error) {
    console.error('删除会话失败:', error)
    ElMessage.error('删除会话失败，请重试')
  }
}

// 保存消息到会话（由后端自动处理，前端无需调用）
const saveMessageToConversation = async (role: string, content: string) => {
  // 后端会自动进行长短记忆持久化，前端无需主动调用保存接口
  // 此函数保留用于兼容，但不执行任何操作
}

// 处理文档上传后，让 AI 分析并回复
const processDocumentWithAI = async (fileName: string, documentType: string) => {
  try {
    const userMessage = `我上传了一份医疗文档：${fileName}（类型：${documentType}），请分析并提取其中的关键信息。`

    const token = localStorage.getItem('token')
    const response = await fetch(`${backendUrl}/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        user_id: userId.value,
        message: userMessage,
        thread_id: threadId.value
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 解析 JSON 响应
    const data = await response.json()

    if (data.success && data.message) {
      // 更新 AI 消息内容
      const lastMessage = messages.value[messages.value.length - 1]
      if (lastMessage && lastMessage.role === 'assistant') {
        messages.value[messages.value.length - 1] = {
          ...lastMessage,
          content: data.message,
          timestamp: new Date()
        }
        await nextTick()
        scrollToBottom()
      }
    }
  } catch (error) {
    console.error('AI 分析文档失败:', error)
    ElMessage.error('AI 分析文档失败')

    // 更新错误提示
    const lastMessage = messages.value[messages.value.length - 1]
    if (lastMessage && lastMessage.role === 'assistant') {
      messages.value[messages.value.length - 1] = {
        ...lastMessage,
        content: '抱歉，分析文档时出现错误，请稍后重试。',
        timestamp: new Date()
      }
    }
  }
}

// 更新会话信息
const updateConversation = async () => {
  // 当消息发送后，会调用saveMessageToConversation来保存消息
  // 这里可以添加额外的会话更新逻辑
}

// 保存消息到会话（由后端自动处理，前端无需调用）
const saveMessage = async (role: string, content: string) => {
  // 后端会自动进行长短记忆持久化，前端无需主动调用保存接口
}

// 登出
const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  user.value = null
  router.push('/login')
  ElMessage.success('已登出')
}

// 转换Markdown为HTML
const renderContent = (content: string) => {
  if (!content) return ''

  console.log('[renderContent] 原始 Markdown 内容:', content)

  // 配置marked库
  const markedOptions = {
    breaks: true,  // 支持换行
    gfm: true,     // 支持GitHub风格的Markdown
    tables: true,  // 支持表格
    headerIds: false, // 不生成header id
    mangle: false  // 不混淆邮件地址
  }

  // 直接渲染，不做额外预处理
  // 后端返回的内容已经有正确的 Markdown 格式
  const html = marked(content, markedOptions)
  console.log('[renderContent] 渲染后的 HTML:', html)

  return html
}

// 滚动到最新消息
const scrollToBottom = () => {
  setTimeout(() => {
    if (messagesContainerRef.value) {
      messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight
    }
  }, 50)
}

// 开始打字机效果
const startTypeWriter = (assistantMessageId: number) => {
  // 清除之前的定时器
  if (typingTimer.value) {
    clearInterval(typingTimer.value)
  }

  currentAiContent.value = ''
  isTyping.value = true

  let index = 0
  const content = pendingContent.value

  typingTimer.value = window.setInterval(() => {
    if (index < content.length) {
      currentAiContent.value += content.charAt(index)
      messages.value[assistantMessageId].content = currentAiContent.value
      scrollToBottom()
      index++
    } else {
      // 打字结束
      clearInterval(typingTimer.value!)
      typingTimer.value = null
      isTyping.value = false
      currentAiContent.value = ''
      pendingContent.value = ''
    }
  }, 30) // 打字速度，每30毫秒打一个字
}

const chatHistory = computed(() => {
  return messages.value.filter(msg => msg.role === 'user' || msg.role === 'assistant')
})

const handleSend = async () => {
  if (!inputMessage.value.trim()) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // 检查是否包含偏好设置指令
  const isPreferenceCommand = checkPreferenceCommand(userMessage)

  // 无论是否是偏好设置指令，都添加到聊天记录中
  messages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  })
  scrollToBottom()

  // 如果是偏好设置指令，添加一个确认消息
  if (isPreferenceCommand) {
    messages.value.push({
      role: 'assistant',
      content: '偏好设置已保存',
      timestamp: new Date()
    })
    scrollToBottom()
    return // 不发送到后端
  }

  try {


    const assistantMessageId = messages.value.length
    messages.value.push({
      role: 'assistant',
      content: '',
      timestamp: new Date()
    })
    scrollToBottom()

    const token = localStorage.getItem('token')
    const response = await fetch(`${backendUrl}/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        user_id: userId.value,
        message: userMessage,
        thread_id: threadId.value
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 解析 JSON 响应（非流式）
    const data = await response.json()

    if (data.success && data.message) {
      // 一次性更新消息内容
      const lastMessage = messages.value[messages.value.length - 1]
      if (lastMessage && lastMessage.role === 'assistant') {
        messages.value[messages.value.length - 1] = {
          ...lastMessage,
          content: data.message,
          timestamp: new Date()
        }
        await nextTick()
        scrollToBottom()
      }
    }

    // 消息保存由后端自动处理，前端无需调用 save_message 接口
    // 长短记忆持久化由后端 LangGraph 自动完成
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('请求已取消')
    } else {
      console.error('发送消息失败:', error)
      ElMessage.error('发送消息失败，请重试')
    }
  } finally {
    // 更新会话信息
    updateConversation()
  }
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}



// 通过聊天方式设置偏好
const handleSetPreference = async (key: string, value: string) => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.post(`${backendUrl}/preferences/save`, {}, {
      params: {
        user_id: userId.value,
        key: key,
        value: value
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 200) {
      ElMessage.success('偏好设置成功')
    }
  } catch (error) {
    console.error('设置偏好失败:', error)
    ElMessage.error('设置偏好失败，请重试')
  } finally {
    // 更新会话信息
    updateConversation()
  }
}

// 检查消息是否包含偏好设置指令
const checkPreferenceCommand = (message: string) => {
  const preferenceRegex = /设置偏好：(\w+)=([^\n]+)/
  const match = message.match(preferenceRegex)
  if (match) {
    const key = match[1].trim()
    const value = match[2].trim()
    handleSetPreference(key, value)
    return true
  }
  return false
}

// 处理文件上传
const handleFileUpload = async (file: any) => {
  try {
    // 询问用户文档类型
    const documentType = prompt('请选择文档类型:', '病历本')
    if (!documentType) return

    // 显示上传中状态
    isUploading.value = true
    uploadProgress.value = 0

    // 模拟进度条动画
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += Math.random() * 15
      }
    }, 500)

    const formData = new FormData()
    formData.append('file', file.raw)
    formData.append('document_type', documentType)
    formData.append('user_id', userId.value)

    const token = localStorage.getItem('token')
    const response = await axios.post(`${backendUrl}/documents/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${token}`
      }
    })

    clearInterval(progressInterval)
    uploadProgress.value = 100

    if (response.status === 200) {
      uploadedFiles.value.push(file)

      // 自动发送消息给 AI，让 AI 读取并回复
      const fileName = file.name || file.raw?.name || '医疗文档'
      const userMessage = `我上传了一份医疗文档：${fileName}`

      // 添加用户消息到界面
      messages.value.push({
        role: 'user',
        content: userMessage,
        timestamp: new Date()
      })

      // 添加 AI 占位消息
      messages.value.push({
        role: 'assistant',
        content: '',
        timestamp: new Date()
      })

      scrollToBottom()

      // 调用 AI 接口，让 AI 分析文档并回复
      await processDocumentWithAI(fileName, documentType)

      // 完成后关闭上传状态
      setTimeout(() => {
        isUploading.value = false
        uploadProgress.value = 0
      }, 500)
      ElMessage.success('文档上传并分析完成！')
    }
  } catch (error) {
    console.error('上传文件失败:', error)
    clearInterval(progressInterval)
    isUploading.value = false
    uploadProgress.value = 0
    ElMessage.error('上传文件失败，请重试')
  }
  return false // 阻止自动上传
}

// 查看文档列表（功能已移除，仅保留函数占位）
const viewDocuments = async () => {
  // 文档列表功能已移除，智能体直接读取医疗文档内容
  ElMessage.info('医疗文档由智能体直接读取，无需手动查看列表')
}

// 加载历史聊天记录
const loadChatHistory = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`${backendUrl}/preferences/get_medical_history`, {
      params: {
        user_id: userId.value
      },
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 200) {
      const medicalHistory = response.data.medical_history
      if (medicalHistory && medicalHistory !== '没有找到医疗历史') {
        // 解析医疗历史，添加到聊天记录中
        const historyLines = medicalHistory.split('\n\n')
        historyLines.forEach((line: string) => {
          if (line.includes('用户:') && line.includes('助手:')) {
            const userMatch = line.match(/用户: (.*?)\\n助手:/)
            const assistantMatch = line.match(/助手: (.*)/)
            if (userMatch && assistantMatch) {
              // 添加用户消息
              messages.value.push({
                role: 'user',
                content: userMatch[1].trim(),
                timestamp: new Date()
              })
              // 添加助手消息
              messages.value.push({
                role: 'assistant',
                content: assistantMatch[1].trim(),
                timestamp: new Date()
              })
            }
          }
        })
        scrollToBottom()
      }
    }
  } catch (error) {
    console.error('加载历史聊天记录失败:', error)
  }
}

onMounted(() => {
  checkLoginStatus()
  // 加载会话列表
  loadConversations()
  scrollToBottom()
})
</script>

<template>
  <div class="langchain-style">
    <header class="langchain-header">
      <div class="header-content">
        <div class="logo">
          <span class="logo-text">小滴智能医疗助手</span>
        </div>
        <div class="user-info">
          <span class="user-id" v-if="user">{{ user.username }}</span>
          <el-button type="text" class="logout-button" @click="handleLogout" v-if="user">
            登出
          </el-button>
        </div>
      </div>
    </header>

    <div class="main-content">
      <!-- 左侧会话列表 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>会话</h3>
          <el-button
            class="new-conversation-btn"
            size="small"
            @click="createNewConversation"
          >
            <el-icon><Plus /></el-icon>
            新会话
          </el-button>
        </div>
        <div class="conversations-list">
          <div
            v-for="conversation in conversations"
            :key="conversation.id"
            class="conversation-item"
            :class="{ active: currentConversation === conversation.id }"
            @click="selectConversation(conversation.id)"
          >
            <div class="conversation-info">
              <div class="conversation-title">{{ conversation.title }}</div>
              <div class="conversation-last-message">{{ conversation.lastMessage }}</div>
              <div class="conversation-time">{{ conversation.lastActive.toLocaleTimeString() }}</div>
            </div>
            <el-popconfirm
              title="确定删除此会话吗？"
              @confirm="deleteConversation(conversation.id)"
            >
              <template #reference>
                <el-button
                  class="delete-conversation-btn"
                  size="small"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>

      <!-- 右侧聊天区域 -->
      <div class="chat-area">
        <div class="messages-container" ref="messagesContainerRef">
          <div
            v-for="(msg, index) in messages"
            :key="`msg-${index}-${msg.timestamp.getTime()}`"
            class="message"
            :class="`message-${msg.role}`"
          >
            <div class="message-content">
              <div class="message-role">
                {{ msg.role === 'user' ? '我' : '医疗助手' }}
              </div>
              <div class="message-text" v-html="renderContent(msg.content)"></div>
              <div class="message-time">
                {{ msg.timestamp.toLocaleTimeString() }}
              </div>
            </div>
          </div>
        </div>

        <div class="input-section">
          <div class="upload-section">
            <el-upload
              class="upload-demo"
              action=""
              :auto-upload="false"
              :on-change="handleFileUpload"
              :show-file-list="false"
              accept=".pdf"
            >
              <el-button class="langchain-button secondary">
                <el-icon><Upload /></el-icon>
                上传医疗文档
              </el-button>
            </el-upload>

          </div>
          <div class="input-container">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="2"
              placeholder="输入您的医疗问题，按 Enter 发送，Shift+Enter 换行"
              @keydown="handleKeyDown"
              resize="none"
            />
            <div class="input-actions">
              <el-button
                class="langchain-button primary"
                :disabled="!inputMessage.trim()"
                @click="handleSend"
              >
                <el-icon><MessageIcon /></el-icon>
                发送
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <footer class="langchain-footer">
      <div class="footer-content">
        <div class="footer-copyright">
          © 2026 小滴智能医疗助手 | 基于 LangChain 构建
        </div>
      </div>
    </footer>
  </div>

  <!-- 文档上传提示框 -->
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
</template>

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

/* 主内容区域 */
.main-content {
  display: flex;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  height: calc(100vh - 140px); /* 固定高度，减去头部和底部 */
  gap: 20px;
}

/* 左侧会话列表 */
.sidebar {
  width: 300px;
  background: rgba(15, 15, 25, 0.5);
  border: 1px solid rgba(50, 200, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  height: 100%; /* 固定高度 */
  overflow: hidden; /* 防止溢出 */
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid rgba(50, 200, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #32c8ff;
}

.new-conversation-btn {
  background: rgba(50, 200, 255, 0.1);
  color: #32c8ff;
  border: 1px solid rgba(50, 200, 255, 0.3);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  transition: all 0.3s ease;
}

.new-conversation-btn:hover {
  background: rgba(50, 200, 255, 0.2);
  border-color: #32c8ff;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  max-height: calc(100% - 70px); /* 减去头部高度 */
}

.conversation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: 8px;
  background: rgba(25, 25, 40, 0.3);
  border: 1px solid rgba(50, 200, 255, 0.1);
}

.conversation-item:hover {
  background: rgba(25, 25, 40, 0.5);
  border-color: rgba(50, 200, 255, 0.2);
}

.conversation-item.active {
  background: rgba(50, 200, 255, 0.1);
  border-color: rgba(50, 200, 255, 0.3);
}

.conversation-info {
  flex: 1;
  min-width: 0;
  margin-right: 10px;
}

.conversation-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-id {
  font-size: 12px;
  color: rgba(50, 200, 255, 0.7);
  font-weight: normal;
}

.conversation-last-message {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.delete-conversation-btn {
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  transition: all 0.3s ease;
  opacity: 0;
  visibility: hidden;
}

.conversation-item:hover .delete-conversation-btn {
  opacity: 1;
  visibility: visible;
}

.delete-conversation-btn:hover {
  background: rgba(255, 87, 34, 0.1);
  color: #ff5722;
}

/* 右侧聊天区域 */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%; /* 固定高度 */
  overflow: hidden; /* 防止溢出 */
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

.logout-button {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  padding: 6px 12px;
  background: transparent;
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-radius: 16px;
  transition: all 0.3s ease;
}

.logout-button:hover {
  color: #32c8ff;
  border-color: #32c8ff;
  background: rgba(50, 200, 255, 0.1);
}

.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
  min-height: 70vh;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.messages-container {
  flex: 1;
  max-height: calc(100% - 180px); /* 固定高度，减去输入区域 */
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 30px;
  background: rgba(15, 15, 25, 0.5);
  border: 1px solid rgba(50, 200, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  overflow-y: auto; /* 内容超出时显示滚动条 */
}

.message {
  max-width: 80%;
  padding: 16px 20px;
  border-radius: 12px;
  animation: fadeIn 0.3s ease;
  position: relative;
  background: linear-gradient(135deg, rgba(50, 200, 255, 0.05) 0%, rgba(30, 144, 255, 0.05) 100%);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-user {
  align-self: flex-end;
  background: rgba(30, 144, 255, 0.15);
  border: 1px solid rgba(30, 144, 255, 0.3);
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 15px rgba(30, 144, 255, 0.2);
}

.message-assistant {
  align-self: flex-start;
  background: rgba(50, 200, 255, 0.1);
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-bottom-left-radius: 4px;
  box-shadow: 0 4px 15px rgba(50, 200, 255, 0.15);
}

.message-role {
  font-size: 12px;
  font-weight: 600;
  color: #32c8ff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.message-text {
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
  color: rgba(255, 255, 255, 0.9);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Markdown 内容样式重置 */
.message-text > *:first-child {
  margin-top: 0;
}

.message-text > *:last-child {
  margin-bottom: 0;
}

/* Markdown 样式 */
.message-text h1,
.message-text h2,
.message-text h3,
.message-text h4,
.message-text h5,
.message-text h6 {
  color: #32c8ff;
  margin-top: 0.6em;
  margin-bottom: 0.3em;
  font-weight: 600;
  line-height: 1.3;
}

.message-text h1 {
  font-size: 1.4em;
  border-bottom: 1px solid rgba(50, 200, 255, 0.3);
  padding-bottom: 0.2em;
}

.message-text h2 {
  font-size: 1.25em;
}

.message-text h3 {
  font-size: 1.1em;
}

.message-text h4,
.message-text h5,
.message-text h6 {
  font-size: 1em;
}

.message-text p {
  margin-top: 0.3em;
  margin-bottom: 0.5em;
  line-height: 1.6;
}

.message-text p:empty {
  display: none;
}

.message-text ul,
.message-text ol {
  margin-top: 0.2em;
  margin-bottom: 0.5em;
  padding-left: 1.2em;
}

.message-text li {
  margin-bottom: 0.25em;
  line-height: 1.5;
}

.message-text li:last-child {
  margin-bottom: 0;
}

.message-text blockquote {
  margin: 0.5em 0;
  padding-left: 1em;
  border-left: 3px solid rgba(50, 200, 255, 0.3);
  color: rgba(255, 255, 255, 0.7);
}

.message-text hr {
  border: none;
  border-top: 1px solid rgba(50, 200, 255, 0.3);
  margin: 0.8em 0;
}

.message-text strong {
  color: #32c8ff;
  font-weight: 600;
}

.message-text em {
  color: rgba(255, 255, 255, 0.8);
  font-style: italic;
}

.message-text code {
  background: rgba(50, 200, 255, 0.1);
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-size: 0.9em;
}

.message-text pre {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.8em;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.message-text pre code {
  background: none;
  padding: 0;
}

.message-text table {
  border-collapse: collapse;
  margin: 0.5em 0;
  width: 100%;
}

.message-text th,
.message-text td {
  border: 1px solid rgba(50, 200, 255, 0.2);
  padding: 0.4em 0.6em;
  text-align: left;
}

.message-text th {
  background: rgba(50, 200, 255, 0.1);
  font-weight: 600;
}

.message-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  text-align: right;
  margin-top: 4px;
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 30px;
  background: rgba(15, 15, 25, 0.5);
  border: 1px solid rgba(50, 200, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.upload-section {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.input-container {
  display: flex;
  gap: 12px;
  align-items: stretch;
}

.input-actions {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.input-actions .el-button {
  height: 100%;
}

.quick-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-start;
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
  display: flex;
  align-items: center;
  gap: 5px;
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

:deep(.el-textarea__inner) {
  background: rgba(25, 25, 40, 0.8);
  border: 1px solid rgba(50, 200, 255, 0.2);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.9);
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  transition: all 0.3s ease;
}

:deep(.el-textarea__inner:focus) {
  border-color: #32c8ff;
  box-shadow: 0 0 0 2px rgba(50, 200, 255, 0.2);
  background: rgba(25, 25, 40, 0.9);
}

:deep(.el-textarea__inner::placeholder) {
  color: rgba(255, 255, 255, 0.4);
}

:deep(.el-input__wrapper) {
  box-shadow: none !important;
}

.langchain-footer {
  background: rgba(10, 10, 15, 0.95);
  border-top: 1px solid rgba(50, 200, 255, 0.2);
  backdrop-filter: blur(10px);
  margin-top: 40px;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 30px 20px;
  display: flex;
  flex-direction: column;
}

.footer-copyright {
  text-align: center;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
}

/* 文档上传提示框样式 */
.upload-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(5px);
}

.upload-dialog {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 40px 50px;
  box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
  text-align: center;
  min-width: 400px;
  animation: dialog-slide-in 0.3s ease-out;
}

@keyframes dialog-slide-in {
  from {
    opacity: 0;
    transform: translateY(-30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.upload-icon {
  color: #ffffff;
  margin-bottom: 20px;
  animation: icon-bounce 1.5s infinite;
}

@keyframes icon-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.upload-text {
  color: #ffffff;
  margin-bottom: 25px;
}

.upload-text h3 {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 10px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.upload-text p {
  font-size: 14px;
  margin: 0;
  opacity: 0.9;
}

.upload-progress {
  width: 100%;
}

.upload-progress :deep(.el-progress-bar__outer) {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 10px;
}

.upload-progress :deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
  border-radius: 10px;
  transition: width 0.3s ease;
}

/* 淡入淡出动画 */
.upload-fade-enter-active,
.upload-fade-leave-active {
  transition: opacity 0.3s ease;
}

.upload-fade-enter-from,
.upload-fade-leave-to {
  opacity: 0;
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

  .upload-section {
    flex-wrap: wrap;
  }

  .quick-actions {
    flex-wrap: wrap;
  }
}
</style>

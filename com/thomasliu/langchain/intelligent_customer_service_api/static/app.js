/**
 * StreamUI JS 工具库
 * SSE 流式连接 + 打字机效果
 */
function createSSE(url, options = {}) {
    const {
        onToken = () => {},
        onDone = () => {},
        onError = () => {},
        onReferences = () => {},
        onThinking = () => {},
    } = options;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
            eventSource.close();
            onDone();
            return;
        }
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'token') {
                onToken(data.content);
            } else if (data.type === 'thinking') {
                onThinking(data.content);
            } else if (data.type === 'references') {
                onReferences(data.references);
            } else if (data.type === 'error') {
                onError(data.content);
            } else {
                onToken(data.content || '');
            }
        } catch {
            onToken(event.data);
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        onError('连接中断');
    };

    return eventSource;
}

class Typewriter {
    constructor(element, speed = 30) {
        this.element = element;
        this.speed = speed;
        this.buffer = '';
        this.index = 0;
        this.timeout = null;
        this.done = false;
    }

    append(text) {
        this.buffer += text;
        if (!this.timeout) {
            this._tick();
        }
    }

    _tick() {
        if (this.index < this.buffer.length) {
            const charsToAdd = Math.min(3, this.buffer.length - this.index);
            this.element.innerHTML += this.buffer.slice(this.index, this.index + charsToAdd);
            this.index += charsToAdd;
            this.element.scrollTop = this.element.scrollHeight;
            this.timeout = setTimeout(() => this._tick(), this.speed);
        } else {
            this.timeout = null;
            if (this.done) {
                this.element.classList.remove('streaming-cursor');
            }
        }
    }

    finish() {
        this.done = true;
        if (this.index < this.buffer.length) {
            this.element.innerHTML += this.buffer.slice(this.index);
            this.index = this.buffer.length;
        }
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
        }
        this.element.classList.remove('streaming-cursor');
    }

    reset() {
        if (this.timeout) clearTimeout(this.timeout);
        this.buffer = '';
        this.index = 0;
        this.timeout = null;
        this.done = false;
        this.element.innerHTML = '';
        this.element.classList.remove('streaming-cursor');
    }
}

function showStatus(element, message, type = 'info') {
    element.className = `status status-${type}`;
    element.textContent = message;
    element.style.display = 'block';
}

function hideStatus(element) {
    element.style.display = 'none';
}

function formatDate() {
    return new Date().toLocaleString('zh-CN');
}

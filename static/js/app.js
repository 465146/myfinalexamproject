// 校园智能办事助手 - 前端交互逻辑

const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const analysisContent = document.getElementById('analysisContent');

let sessionId = null;  // 服务端维护的会话ID
let currentAiType = 'fastgpt';  // 当前AI类型
let isLoading = false;

// 初始化侧边栏导航
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const intent = item.dataset.intent;
        const intentNames = {
            course: '课程咨询',
            scholarship: '奖学金',
            internship: '实习就业',
            academic_affairs: '教务事务',
            competition: '竞赛活动',
            campus_life: '校园生活'
        };
        const query = `我想了解${intentNames[intent] || ''}相关的信息`;
        userInput.value = query;
        sendMessage();
    });
});

// 发送消息
async function sendMessage() {
    const question = userInput.value.trim();
    if (!question || isLoading) return;

    // 添加用户消息到界面
    appendMessage('user', question);
    userInput.value = '';
    autoResizeInput();

    // 显示加载
    isLoading = true;
    sendBtn.disabled = true;
    const loadingId = showLoading();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                session_id: sessionId,
                ai_type: currentAiType
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || '请求失败');
        }

        const data = await response.json();

        // 保存服务端返回的 session_id
        sessionId = data.session_id;

        // 移除加载动画
        removeLoading(loadingId);

        // 添加机器人回复
        appendMessage('bot', data.answer, data.quick_replies, data.sources);

        // 更新分析面板
        updateAnalysis(data);

    } catch (error) {
        removeLoading(loadingId);
        appendMessage('bot', '抱歉，发生了错误：' + error.message);
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// 快捷回复
function sendQuickReply(text) {
    userInput.value = text;
    sendMessage();
}

// 添加消息到聊天区
function appendMessage(role, text, quickReplies = [], sources = []) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? '😊' : '🤖';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = text;
    contentDiv.appendChild(textDiv);

    // 来源标签
    if (sources && sources.length > 0) {
        const sourceDiv = document.createElement('div');
        sourceDiv.className = 'quick-replies';
        sources.forEach(s => {
            const tag = document.createElement('span');
            tag.className = 'source-tag';
            tag.textContent = `📎 ${s.source || '知识库'}`;
            sourceDiv.appendChild(tag);
        });
        contentDiv.appendChild(sourceDiv);
    }

    // 快捷回复
    if (quickReplies && quickReplies.length > 0) {
        const replyDiv = document.createElement('div');
        replyDiv.className = 'quick-replies';
        quickReplies.forEach(reply => {
            const btn = document.createElement('button');
            btn.className = 'quick-reply-btn';
            btn.textContent = reply;
            btn.onclick = () => sendQuickReply(reply);
            replyDiv.appendChild(btn);
        });
        contentDiv.appendChild(replyDiv);
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

// 显示加载动画
function showLoading() {
    const id = 'loading-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🤖';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = '<span></span><span></span><span></span>';

    contentDiv.appendChild(typing);
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// 更新分析面板
function updateAnalysis(data) {
    if (!data) return;

    let html = '';

    // 意图识别
    if (data.intent) {
        const intentNames = {
            course: '📚 课程咨询',
            scholarship: '🏆 奖学金',
            internship: '💼 实习就业',
            academic_affairs: '📋 教务事务',
            competition: '🎯 竞赛活动',
            campus_life: '🏠 校园生活',
            general: '💬 一般咨询'
        };
        const intentName = intentNames[data.intent.intent] || data.intent.intent;
        const confidence = Math.round((data.intent.confidence || 0) * 100);

        html += `
        <div class="analysis-section">
            <h4>🎯 意图识别</h4>
            <div class="intent-badge">${intentName}</div>
            <div style="margin-top:8px;font-size:13px;color:var(--text-light)">
                子意图：${data.intent.sub_intent || '-'}
            </div>
            <div style="margin-top:8px;font-size:12px;color:var(--text-light)">置信度：${confidence}%</div>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width:${confidence}%"></div>
            </div>
        </div>`;
    }

    // 信息抽取
    if (data.entities && data.entities.length > 0) {
        html += `
        <div class="analysis-section">
            <h4>🔍 信息抽取</h4>`;
        data.entities.forEach(ent => {
            html += `
            <div class="entity-item">
                <span class="entity-type">${ent.type}</span>
                <span class="entity-value">${ent.value}</span>
            </div>`;
        });
        html += `</div>`;
    }

    // 知识库来源
    if (data.sources && data.sources.length > 0) {
        html += `
        <div class="analysis-section">
            <h4>📖 知识库来源</h4>`;
        data.sources.forEach(src => {
            html += `
            <div class="source-item">
                <div class="source-name">${src.source || '知识库'}</div>
                <div style="margin-top:4px;color:var(--text-light)">${(src.content || '').substring(0, 80)}...</div>
            </div>`;
        });
        html += `</div>`;
    }

    // AI类型标识
    html += `
    <div class="analysis-section">
        <h4>⚙️ 当前模式</h4>
        <div class="entity-item">
            <span class="entity-type">AI</span>
            <span class="entity-value">${data.ai_type === 'fastgpt' ? 'FastGPT 知识库' : 'DeepSeek 对话'}</span>
        </div>
    </div>`;

    if (!html) {
        html = '<div class="analysis-placeholder">暂无分析数据</div>';
    }

    analysisContent.innerHTML = html;
}

// 清空对话
clearBtn.addEventListener('click', async () => {
    // 1. 处理加载状态
    if (isLoading) {
        isLoading = false;
        sendBtn.disabled = false;
        const loadingElements = document.querySelectorAll('[id^="loading-"]');
        loadingElements.forEach(el => el.remove());
    }

    // 2. 清除服务端会话
    if (sessionId) {
        try {
            await fetch(`/api/chat/${sessionId}`, { method: 'DELETE' });
        } catch (e) {
            console.log('清除会话失败:', e);
        }
    }
    sessionId = null;

    // 3. 保持布局稳定：使用 opacity 代替 display 避免 Grid 塌陷
    chatMessages.style.opacity = '0';
    chatMessages.style.pointerEvents = 'none';

    // 清空内容
    while (chatMessages.firstChild) {
        chatMessages.removeChild(chatMessages.firstChild);
    }

    // 重置分析面板
    if (analysisContent) {
        analysisContent.innerHTML = '<div class="analysis-placeholder">发送问题后，这里将显示意图识别、信息抽取和分析结果</div>';
    }

    // 4. 恢复显示并添加新消息
    requestAnimationFrame(() => {
        chatMessages.style.opacity = '1';
        chatMessages.style.pointerEvents = 'auto';

        appendMessage('bot', '对话已清空，有什么新的问题吗？', [
            '如何选课？', '奖学金种类', '补考报名', '图书馆时间'
        ]);
    });
});

// 键盘事件
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 自动调整输入框高度
userInput.addEventListener('input', autoResizeInput);

function autoResizeInput() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
}

// 滚动到底部
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

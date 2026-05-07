const MAX_MESSAGES = 10;
const MAX_SESSIONS = 2;
const MAX_PROMPT_LENGTH = 500;
const RESET_HOURS = 1;
const STORAGE_KEY = 'coursegenie_chat_sessions_v1';

const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatHistory = document.getElementById('chat-history');
const sessionList = document.getElementById('session-list');
const chatTitleEl = document.getElementById('chat-title');
const messageCounter = document.getElementById('message-counter');
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('main-content');
const toast = document.getElementById('toast');
const sessionMenu = document.getElementById('session-menu');

let sessions = [];
let currentSessionId = null;
let currentMenuSessionId = null;
let toastTimeout = null;
let isWaitingForResponse = false;

window.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    loadSessions();
    renderSidebar();
    if (sessions.length > 0 && currentSessionId) {
        openSession(currentSessionId);
    } else {
        setSessionTitle('CourseGenie');
        showWelcomeScreen();
        updateCounter([]);
    }
    updateSidebarState();

    chatForm.addEventListener('submit', sendMessage);
    document.addEventListener('click', handlePageClick);
    chatInput.addEventListener('input', updateCharCounter);
    chatInput.addEventListener('input', updateCharCounterDisplay);
    chatInput.addEventListener('paste', handlePaste);
    chatInput.addEventListener('keypress', handleCharLimit);
    chatInput.addEventListener('click', () => {
        if (sidebar.classList.contains('collapsed') === false) {
            toggleSidebar();
        }
    });
});

function loadSessions() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            sessions = Array.isArray(parsed.sessions) ? parsed.sessions : [];
            currentSessionId = parsed.currentSessionId || null;
        } catch (error) {
            console.warn('Could not parse stored sessions', error);
            sessions = [];
            currentSessionId = null;
        }
    }

    if (!Array.isArray(sessions) || sessions.length === 0) {
        sessions = [];
        currentSessionId = null;
    }

    if (currentSessionId && !sessions.some(s => s.id === currentSessionId)) {
        currentSessionId = null;
    }
}

function saveSessions() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessions, currentSessionId }));
}

function getCurrentSession() {
    return sessions.find(session => session.id === currentSessionId) || null;
}

function ensureCurrentSession() {
    let session = getCurrentSession();
    if (!session) {
        const sessionCount = sessions.length + 1;
        const newSession = createDefaultSession(`Chat session ${sessionCount}`);
        sessions.unshift(newSession);
        currentSessionId = newSession.id;
        saveSessions();
        renderSidebar();
        setSessionTitle(newSession.name);
        session = newSession;
    }
    return session;
}

function createDefaultSession(name) {
    return {
        id: 'session-' + Date.now(),
        name: name || `Chat session ${sessions.length + 1}`,
        createdAt: new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
        history: [],
        limitReachedAt: null,
    };
}

function createNewChat() {
    if (sessions.length >= MAX_SESSIONS) {
        showToast('Maximum of 3 chat sessions reached. Delete an existing session to create a new one.');
        return;
    }

    const sessionCount = sessions.length + 1;
    const newSession = createDefaultSession(`Chat session ${sessionCount}`);
    sessions.unshift(newSession);
    currentSessionId = newSession.id;
    saveSessions();
    renderSidebar();
    openSession(newSession.id);
    closeSessionMenu();
    showToast('New chat session started.');
}

function renderSidebar() {
    sessionList.innerHTML = '';

    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = 'history-item';
        if (session.id === currentSessionId) {
            item.classList.add('active');
        }

        const lastUpdated = new Date(session.lastUpdated || session.createdAt).toLocaleDateString();
        item.innerHTML = `
            <div class="history-content">
                <span class="history-text">${escapeHtml(session.name)}</span>
            </div>
            ${session.id === currentSessionId ? '<button class="session-menu-btn" type="button" aria-label="Chat menu">&hellip;</button>' : ''}
        `;

        const menuButton = item.querySelector('.session-menu-btn');
        if (menuButton) {
            menuButton.addEventListener('click', (event) => {
                event.stopPropagation();
                openSessionMenu(event, session.id);
            });
        }

        item.addEventListener('click', () => {
            openSession(session.id);
            closeSessionMenu();
        });

        sessionList.appendChild(item);
    });

    // Update new chat button state
    const newChatBtn = document.getElementById('new-chat-btn');
    if (sessions.length >= MAX_SESSIONS) {
        newChatBtn.disabled = true;
        newChatBtn.style.opacity = '0.5';
        newChatBtn.style.cursor = 'not-allowed';
    } else {
        newChatBtn.disabled = false;
        newChatBtn.style.opacity = '1';
        newChatBtn.style.cursor = 'pointer';
    }
}

function openSession(sessionId) {
    const newSession = sessions.find(session => session.id === sessionId);
    if (!newSession) {
        currentSessionId = null;
        saveSessions();
        renderSidebar();
        setSessionTitle('CourseGenie');
        chatHistory.innerHTML = '';
        showWelcomeScreen();
        return;
    }

    if (currentSessionId === sessionId && !chatHistory.innerHTML.trim()) {
        renderCurrentSession();
        restoreServerSession(newSession.history);
        return;
    }

    currentSessionId = newSession.id;
    saveSessions();
    renderSidebar();
    renderCurrentSession();
    restoreServerSession(newSession.history);
}

function renderCurrentSession() {
    const session = getCurrentSession();
    if (!session) {
        setSessionTitle('CourseGenie');
        chatHistory.innerHTML = '';
        showWelcomeScreen();
        updateCounter([]);
        updateCharCounter();
        return;
    }
    setSessionTitle(session.name);
    renderHistory(session.history);
    updateCounter(session.history);
    updateCharCounter();
}

function setSessionTitle(name) {
    chatTitleEl.innerHTML = `<span class="title-text">${escapeHtml(name)}</span>`;
    checkHeaderOverflow();
}

function checkHeaderOverflow() {
    const titleElement = document.querySelector('.title-text');
    if (!titleElement) return;
    
    const headerTitle = document.querySelector('.header-title');
    if (titleElement.scrollWidth > headerTitle.clientWidth) {
        titleElement.style.whiteSpace = 'nowrap';
        titleElement.style.overflow = 'hidden';
        titleElement.style.textOverflow = 'ellipsis';
    } else {
        titleElement.style.whiteSpace = 'normal';
        titleElement.style.overflow = 'visible';
        titleElement.style.textOverflow = 'clip';
    }
}

function renderHistory(history) {
    chatHistory.innerHTML = '';
    if (!history || history.length === 0) {
        showWelcomeScreen();
        return;
    }

    history.forEach(message => {
        appendMessage(message.role === 'user' ? 'You' : 'CourseGenie', message.content, message.role === 'user' ? 'user-message' : 'bot-message');
    });
}

function showWelcomeScreen() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-screen';
    welcomeDiv.innerHTML = `
        <img src="/static/img/coursegenie2.png" class="welcome-icon" alt="CourseGenie">
        <h1 class="welcome-title">How can I help you?</h1>
        <div class="example-prompts">
            <div class="prompt-card" onclick="fillExample('I love working with computers and solving problems')">
                <div class="prompt-icon">💻</div>
                <div>I love working with computers and solving problems</div>
            </div>
            <div class="prompt-card" onclick="fillExample('I want to help people and work in healthcare')">
                <div class="prompt-icon">🏥</div>
                <div>I want to help people and work in healthcare</div>
            </div>
            <div class="prompt-card" onclick="fillExample('I enjoy business and entrepreneurship')">
                <div class="prompt-icon">💼</div>
                <div>I enjoy business and entrepreneurship</div>
            </div>
            <div class="prompt-card" onclick="fillExample('What are the prerequisites for Information Technology?')">
                <div class="prompt-icon">📋</div>
                <div>What are the prerequisites for Information Technology?</div>
            </div>
        </div>
    `;
    chatHistory.appendChild(welcomeDiv);
}

function fillExample(question) {
    chatInput.value = question;
    sendMessage(new Event('submit'));
}

async function sendMessage(event) {
    event.preventDefault();

    const message = chatInput.value.trim();
    if (!message) return;

    const currentSession = ensureCurrentSession();
    const remaining = await getRemainingMessages();
    if (remaining <= 0) {
        showLimitReached();
        return;
    }

    const welcomeScreen = document.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.remove();
    }

    chatInput.value = '';
    updateCharCounterDisplay();
    appendMessage('You', message, 'user-message');

    const wasEmpty = currentSession.history.length === 0;
    currentSession.history.push({ role: 'user', content: message });
    currentSession.lastUpdated = new Date().toISOString();

    if (wasEmpty) {
        currentSession.name = generateSmartName(message);
        setSessionTitle(currentSession.name);
        renderSidebar();
    }

    saveSessions();
    updateCounter(currentSession.history);

    const typingId = showTypingIndicator();
    disableInputAndButton();

    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `question=${encodeURIComponent(message)}`,
    })
        .then(async response => {
            const text = await response.text();
            if (!response.ok) {
                throw new Error(text || 'Request failed');
            }
            return text;
        })
        .then(data => {
            removeTypingIndicator(typingId);
            appendMessage('CourseGenie', data, 'bot-message', true);
            const currentSession = getCurrentSession();
            currentSession.history.push({ role: 'assistant', content: data });
            currentSession.lastUpdated = new Date().toISOString();
            saveSessions();
            updateCounter(currentSession.history);
            enableInputAndButton();
            (async () => {
                const remaining = await getRemainingMessages();
                if (remaining <= 0) {
                    showLimitReached();
                }
            })();
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator(typingId);
            appendMessage('CourseGenie', error.message || 'Sorry, something went wrong. Please try again.', 'bot-message', true);
            enableInputAndButton();
            if (error.message && error.message.toLowerCase().includes('limit')) {
                showLimitReached();
            }
        });
}

function appendMessage(role, content, className = 'message', animate = false) {
    const messageElement = document.createElement('div');
    messageElement.className = `message-wrapper ${className}`;
    const isUser = className.includes('user');
    const isBot = className.includes('bot-message');
    
    // Render markdown for bot messages, plain text for user messages
    const displayContent = isBot ? formatMarkdown(content) : escapeHtml(content);
    
    messageElement.innerHTML = `
        <div class="message ${className}">
            <div class="message-content">
                <div class="message-text">${displayContent}</div>
            </div>
        </div>
        <div class="message-actions">
            <button class="action-btn copy-btn" onclick="copyToClipboard(this)" title="Copy">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
            </button>
        </div>
    `;
    chatHistory.appendChild(messageElement);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    if (!isUser && animate && isBot) {
        // For bot messages with markdown, we don't use typeWriter as it expects plain text
        // The markdown is already rendered, so just let it display
    }
}


function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    if (typeof marked !== 'undefined') {
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('Markdown parsing error:', e);
        }
    }

    let formatted = text;
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    formatted = formatted.replace(/\n/g, '<br>');
    formatted = formatted.replace(/^\s*[-•]\s+(.+)$/gm, '<li>$1</li>');
    if (formatted.includes('<li>')) {
        formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    }
    formatted = formatted.replace(/^\s*\d+\.\s+(.+)$/gm, '<li>$1</li>');
    return formatted;
}

function copyToClipboard(button) {
    const messageWrapper = button.closest('.message-wrapper');
    const messageText = messageWrapper.querySelector('.message-text');
    const textToCopy = messageText.innerText || messageText.textContent;

    navigator.clipboard.writeText(textToCopy).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
        `;
        button.classList.add('copied');

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

function showTypingIndicator() {
    const typingId = 'typing-' + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.id = typingId;
    typingDiv.className = 'message-wrapper typing-indicator';
    typingDiv.innerHTML = `
        <div class="message bot-message">
            <div class="message-content">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    chatHistory.appendChild(typingDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return typingId;
}

function removeTypingIndicator(typingId) {
    const typingDiv = document.getElementById(typingId);
    if (typingDiv) {
        typingDiv.remove();
    }
}

async function getRemainingMessages() {
    try {
        const response = await fetch('/limit-status');
        const data = await response.json();
        return Math.max(0, data.max_messages - data.message_count);
    } catch {
        // Fallback
        const currentSession = getCurrentSession();
        const used = currentSession.history.filter(message => message.role === 'user').length;
        return Math.max(0, MAX_MESSAGES - used);
    }
}

function updateCounter(history) {
    // Fetch global limit status
    fetch('/limit-status')
        .then(response => response.json())
        .then(data => {
            const remaining = Math.max(0, data.max_messages - data.message_count);
            messageCounter.textContent = `${remaining} message${remaining === 1 ? '' : 's'} left`;
            messageCounter.classList.toggle('warning', remaining <= 2);

            // Add tooltip
            let tooltip = '';
            if (data.cooldown_remaining) {
                const hours = Math.floor(data.cooldown_remaining / 3600);
                const minutes = Math.floor((data.cooldown_remaining % 3600) / 60);
                tooltip = `Limit reached. Reset in ${hours}h ${minutes}m`;
            } else {
                tooltip = 'Global message limit: 10 per 6 hours';
            }
            messageCounter.title = tooltip;
        })
        .catch(() => {
            // Fallback to local calculation
            const used = history.filter(message => message.role === 'user').length;
            const remaining = Math.max(0, MAX_MESSAGES - used);
            messageCounter.textContent = `${remaining} message${remaining === 1 ? '' : 's'} left`;
            messageCounter.classList.toggle('warning', remaining <= 2);
            messageCounter.title = 'Global message limit: 10 per 6 hours';
        });
}

function disableInputAndButton(message = 'Responding...') {
    chatInput.disabled = true;
    chatInput.setAttribute('placeholder', message);
    chatForm.querySelector('button').disabled = true;
}

function disableButtonOnly(message = 'Free messages exhausted. Start a new chat.') {
    chatInput.disabled = false;
    chatInput.setAttribute('placeholder', message);
    chatForm.querySelector('button').disabled = true;
}

async function enableInputAndButton() {
    const remaining = await getRemainingMessages();
    if (remaining <= 0) {
        chatInput.disabled = false;
        chatInput.setAttribute('placeholder', 'Free messages exhausted. Start a new chat.');
        chatForm.querySelector('button').disabled = true;
        return;
    }
    chatInput.disabled = false;
    chatInput.setAttribute('placeholder', 'Message CourseGenie');
    chatForm.querySelector('button').disabled = false;
    chatInput.focus();
}

function showLimitReached() {
    const currentSession = getCurrentSession();
    if (!currentSession.limitReachedAt) {
        currentSession.limitReachedAt = new Date().toISOString();
        saveSessions();
    }
    disableButtonOnly('Free messages exhausted. Wait 1 hour for reset.');
    showToast('You have run out of free messages for this chat. Wait 1 hour for reset or start a new session.');
}

function restoreServerSession(history) {
    if (!Array.isArray(history) || history.length === 0) {
        return fetch('/start-session', { method: 'POST' }).catch(() => {});
    }

    return fetch('/restore', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ history: buildHistoryPairs(history) }),
    }).catch(() => {});
}

function buildHistoryPairs(history) {
    const pairs = [];
    for (let i = 0; i < history.length; i += 1) {
        const current = history[i];
        if (current.role !== 'user') continue;
        const next = history[i + 1];
        pairs.push({
            question: current.content,
            response: next && next.role === 'assistant' ? next.content : '',
        });
    }
    return pairs.slice(-MAX_MESSAGES);
}

function openSessionMenu(event, sessionId) {
    if (currentMenuSessionId === sessionId && !sessionMenu.hidden) {
        return closeSessionMenu();
    }

    currentMenuSessionId = sessionId;
    sessionMenu.hidden = false;
    const rect = event.currentTarget.getBoundingClientRect();
    sessionMenu.style.top = `${rect.bottom + window.scrollY + 8}px`;
    sessionMenu.style.left = `${Math.max(12, rect.left - 120)}px`;
}

function closeSessionMenu() {
    sessionMenu.hidden = true;
    currentMenuSessionId = null;
}

function handlePageClick(event) {
    if (!sessionMenu.contains(event.target) && !event.target.closest('.session-menu-btn')) {
        closeSessionMenu();
    }
}

function renameSession() {
    if (!currentMenuSessionId) return;
    const session = sessions.find(item => item.id === currentMenuSessionId);
    if (!session) return;

    const newName = prompt('Rename this chat session', session.name);
    if (newName === null) {
        closeSessionMenu();
        return;
    }

    const trimmed = newName.trim();
    if (trimmed.length > 0) {
        session.name = trimmed;
        saveSessions();
        renderSidebar();
        if (session.id === currentSessionId) {
            setSessionTitle(session.name);
        }
        showToast('Chat session renamed.');
    }
    closeSessionMenu();
}

function deleteSession() {
    if (!currentMenuSessionId) return;
    const session = sessions.find(item => item.id === currentMenuSessionId);
    if (!session) return;

    const confirmed = confirm('Delete this chat session permanently?');
    if (!confirmed) {
        closeSessionMenu();
        return;
    }

    sessions = sessions.filter(item => item.id !== currentMenuSessionId);
    if (sessions.length === 0) {
        currentSessionId = null;
        saveSessions();
        renderSidebar();
        chatHistory.innerHTML = '';
        setSessionTitle('CourseGenie');
        showWelcomeScreen();
        showToast('Chat session deleted.');
        closeSessionMenu();
        return;
    }

    if (currentSessionId === currentMenuSessionId) {
        currentSessionId = sessions[0].id;
    }

    saveSessions();
    renderSidebar();
    openSession(currentSessionId);
    showToast('Chat session deleted.');
    closeSessionMenu();
}



function showToast(message, duration = 3800) {
    clearTimeout(toastTimeout);
    toast.textContent = message;
    toast.classList.add('visible');
    toastTimeout = setTimeout(() => {
        toast.classList.remove('visible');
    }, duration);
}

function generateSmartName(message) {
    const lower = message.toLowerCase();
    if (lower.includes('course') || lower.includes('program') || lower.includes('study') || lower.includes('major')) {
        return 'Course Enquiry';
    }
    if (lower.includes('prerequisite') || lower.includes('requirement') || lower.includes('admission')) {
        return 'Admission Info';
    }
    if (lower.includes('career') || lower.includes('job') || lower.includes('work')) {
        return 'Career Advice';
    }
    if (lower.includes('fee') || lower.includes('cost') || lower.includes('tuition')) {
        return 'Fees & Costs';
    }
    if (lower.includes('computer') || lower.includes('it') || lower.includes('software')) {
        return 'IT Programs';
    }
    if (lower.includes('business') || lower.includes('finance') || lower.includes('accounting')) {
        return 'Business Programs';
    }
    if (lower.includes('engineering') || lower.includes('technical')) {
        return 'Engineering Programs';
    }
    if (lower.includes('health') || lower.includes('medical') || lower.includes('nursing')) {
        return 'Health Programs';
    }
    // Default
    return message.length > 20 ? message.substring(0, 20) + '...' : message;
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }
    updateThemeIcon();
}

function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const theme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('theme', theme);
    updateThemeIcon();
}

function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('sidebar-collapsed');
    document.body.classList.toggle('sidebar-closed', sidebar.classList.contains('collapsed'));
}

function updateThemeIcon() {
    const isLight = document.body.classList.contains('light-theme');
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.textContent = isLight ? '☾' : '☀';
        themeToggle.title = isLight ? 'Switch to dark mode' : 'Switch to light mode';
    }
}

function updateSidebarState() {
    document.body.classList.toggle('sidebar-closed', sidebar.classList.contains('collapsed'));
}

function updateCharCounter() {
    const length = chatInput.value.length;
    if (length > MAX_PROMPT_LENGTH) {
        chatForm.querySelector('button').disabled = true;
        showToast('Character limit reached (500 characters max)', 5000);
    } else {
        chatForm.querySelector('button').disabled = false;
    }
    updateCharCounterDisplay();
}

function updateCharCounterDisplay() {
    const length = chatInput.value.length;
    const counter = document.getElementById('char-counter');
    counter.textContent = `${length}/${MAX_PROMPT_LENGTH}`;
    counter.classList.toggle('warning', length >= MAX_PROMPT_LENGTH * 0.9);
    
    if (length > MAX_PROMPT_LENGTH) {
        chatForm.querySelector('button').disabled = true;
    } else {
        chatForm.querySelector('button').disabled = false;
    }
}

function handleCharLimit(event) {
    // Allow typing beyond limit for editing, but send will be blocked
}

function handlePaste(event) {
    const pastedText = (event.clipboardData || window.clipboardData).getData('text');
    const currentLength = chatInput.value.length;
    const newLength = currentLength + pastedText.length;
    
    if (newLength > MAX_PROMPT_LENGTH) {
        event.preventDefault();
        showToast('Cannot paste: would exceed 500 character limit', 5000);
    }
}

function typeWriter(element, text, speed = 5) {
    let i = 0;
    element.innerHTML = '';
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        } else {
            element.innerHTML = formatMarkdown(text);
        }
    }
    type();
}

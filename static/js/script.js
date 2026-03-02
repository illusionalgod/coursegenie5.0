const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatHistory = document.getElementById('chat-history');

// Add initial welcome screen
window.addEventListener('DOMContentLoaded', () => {
    showWelcomeScreen();
    loadTheme();
    checkHeaderOverflow();
});

function checkHeaderOverflow() {
    const chatTitleEl = document.getElementById('chat-title');
    const titleTextEl = chatTitleEl.querySelector('.title-text');
    if (titleTextEl && titleTextEl.scrollWidth > titleTextEl.clientWidth) {
        chatTitleEl.classList.add('has-overflow');
    } else {
        chatTitleEl.classList.remove('has-overflow');
    }
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }
}

function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const theme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('theme', theme);
}

function showWelcomeScreen() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-screen';
    welcomeDiv.innerHTML = `
        <img src="/static/img/coursegenie2.png" class="welcome-icon" alt="CourseGenie">
        <h1 class="welcome-title">How can I help you?</h1>
        <div class="example-prompts">
            <div class="prompt-card" onclick="askExample('I love working with computers and solving problems')">
                <div class="prompt-icon">💻</div>
                <div>I love working with computers and solving problems</div>
            </div>
            <div class="prompt-card" onclick="askExample('I want to help people and work in healthcare')">
                <div class="prompt-icon">🏥</div>
                <div>I want to help people and work in healthcare</div>
            </div>
            <div class="prompt-card" onclick="askExample('I enjoy business and entrepreneurship')">
                <div class="prompt-icon">💼</div>
                <div>I enjoy business and entrepreneurship</div>
            </div>
            <div class="prompt-card" onclick="askExample('What are the prerequisites for Information Technology?')">
                <div class="prompt-icon">📋</div>
                <div>What are the prerequisites for Information Technology?</div>
            </div>
        </div>
    `;
    chatHistory.appendChild(welcomeDiv);
}

function askExample(question) {
    chatInput.value = question;
    sendMessage(new Event('submit'));
}

chatForm.addEventListener('submit', sendMessage);

function sendMessage(event) {
    event.preventDefault();

    const message = chatInput.value;
    chatInput.value = '';

    if (message.trim() === '') {
        return;
    }

    // Remove welcome screen if present
    const welcomeScreen = document.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.remove();
    }

    // Update chat title with first message
    const title = message.length > 30 ? message.substring(0, 30) + '...' : message;
    const chatTitleEl = document.getElementById('chat-title');
    chatTitleEl.innerHTML = `<span class="title-text">${title}</span>`;
    
    // Check overflow
    setTimeout(() => {
        checkHeaderOverflow();
    }, 0);

    disableInputAndButton();

    appendMessage('You', message, 'user-message');
    
    // Show typing indicator
    const typingId = showTypingIndicator();

    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `question=${encodeURIComponent(message)}`,
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Request failed');
            }
            return response.text();
        })
        .then(data => {
            removeTypingIndicator(typingId);
            appendMessage('CourseGenie', data, 'bot-message');
            enableInputAndButton();
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator(typingId);
            appendMessage('CourseGenie', 'Sorry, something went wrong. Please try again.', 'bot-message');
            enableInputAndButton();
        });
}

function appendMessage(role, content, className = 'message') {
    const messageElement = document.createElement('div');
    messageElement.className = `message-wrapper ${className}`;
    
    const isUser = className.includes('user');
    
    messageElement.innerHTML = `
        <div class="message ${className}">
            <div class="message-content">
                <div class="message-header">
                    <span class="message-role">${role}</span>
                </div>
                <div class="message-text">${isUser ? escapeHtml(content) : formatMarkdown(content)}</div>
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
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    // Use marked.js if available, otherwise use basic formatting
    if (typeof marked !== 'undefined') {
        try {
            return marked.parse(text);
        } catch (e) {
            console.error('Markdown parsing error:', e);
        }
    }
    
    // Fallback: Basic markdown formatting
    let formatted = text;
    
    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic *text*
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Code blocks ```code```
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Inline code `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Bullet points
    formatted = formatted.replace(/^\s*[-•]\s+(.+)$/gm, '<li>$1</li>');
    if (formatted.includes('<li>')) {
        formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    }
    
    // Numbered lists
    formatted = formatted.replace(/^\s*\d+\.\s+(.+)$/gm, '<li>$1</li>');
    
    return formatted;
}

function copyToClipboard(button) {
    const messageWrapper = button.closest('.message-wrapper');
    const messageText = messageWrapper.querySelector('.message-text');
    const textToCopy = messageText.innerText || messageText.textContent;
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        // Visual feedback
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

function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        fetch('/clear', { method: 'POST' })
            .then(() => {
                chatHistory.innerHTML = '';
                showWelcomeScreen();
                const chatTitleEl = document.getElementById('chat-title');
                chatTitleEl.innerHTML = '<span class="title-text"></span>';
                chatTitleEl.classList.remove('has-overflow');
            })
            .catch(error => console.error('Error clearing chat:', error));
    }
}

function disableInputAndButton() {
    chatInput.disabled = true;
    chatInput.setAttribute('placeholder', 'Responding....');
    chatForm.querySelector('button').disabled = true;
}

function enableInputAndButton() {
    chatInput.disabled = false;
    chatInput.setAttribute('placeholder', 'Message CourseGenie');
    chatForm.querySelector('button').disabled = false;
    chatInput.focus();
}

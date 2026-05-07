import os
import openai
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from chatbot_logic import get_response, get_moderation, INSTRUCTIONS

# load values from the .env file if it exists
load_dotenv()

# configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# use INSTRUCTIONS imported from chatbot_logic

TEMPERATURE = 0.5
MAX_TOKENS = 200
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 5
# maximum number of user questions per chat session
MAX_SESSION_MESSAGES = 10
# global message limit
GLOBAL_MAX_MESSAGES = 10
COOLDOWN_HOURS = 6
LIMIT_FILE = 'limit_state.json'

def load_limit_state():
    if os.path.exists(LIMIT_FILE):
        try:
            with open(LIMIT_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'ips': {}}

def save_limit_state(state):
    with open(LIMIT_FILE, 'w') as f:
        json.dump(state, f)

def check_global_limit(ip):
    state = load_limit_state()
    user_state = state['ips'].get(ip, {'message_count': 0, 'last_limit_time': None})
    now = datetime.now()
    if user_state['last_limit_time']:
        last_time = datetime.fromisoformat(user_state['last_limit_time'])
        if now - last_time > timedelta(hours=COOLDOWN_HOURS):
            user_state['message_count'] = 0
            user_state['last_limit_time'] = None
            state['ips'][ip] = user_state
            save_limit_state(state)
    return user_state['message_count'] >= GLOBAL_MAX_MESSAGES

def increment_global_count(ip):
    state = load_limit_state()
    user_state = state['ips'].get(ip, {'message_count': 0, 'last_limit_time': None})
    user_state['message_count'] += 1
    if user_state['message_count'] >= GLOBAL_MAX_MESSAGES:
        user_state['last_limit_time'] = datetime.now().isoformat()
    state['ips'][ip] = user_state
    save_limit_state(state)


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/agreement')
def agreement():
    return render_template('agreement.html')

@app.route('/chat', methods=['POST'])
def chat():
    ip = request.remote_addr
    new_question = request.form['question']
    if len(new_question) > 500:
        return jsonify({'error': 'Message too long. Maximum 500 characters.'}), 400

    errors = get_moderation(new_question)
    if errors:
        for error in errors:
            print(error)
        # show errors on the index page
        return jsonify({'error': 'Your message was flagged by content moderation.'}), 400

    # Check global limit
    if check_global_limit(ip):
        return jsonify({'error': 'Free message limit reached. Wait 6 hours for reset.'}), 429

    # Get or initialize chat history from session
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    chat_history = session['chat_history']
    
    if len(chat_history) >= MAX_SESSION_MESSAGES:
        return jsonify({'error': 'Free message limit reached for this session. Start a new chat.'}), 429

    response = get_response(INSTRUCTIONS, chat_history, new_question)
    
    # Update chat history
    chat_history.append((new_question, response))
    # Keep only last 10 exchanges to avoid session getting too large
    session['chat_history'] = chat_history[-MAX_SESSION_MESSAGES:]

    # Increment global count
    increment_global_count(ip)

    return response


@app.route('/api/chat', methods=['POST'])
def api_chat():
    ip = request.remote_addr
    data = request.get_json() or {}
    new_question = data.get('question', '')
    if len(new_question) > 500:
        return jsonify({'error': 'Message too long. Maximum 500 characters.'}), 400

    errors = get_moderation(new_question)
    if errors:
        return jsonify({'errors': errors}), 400
    
    # Check global limit
    if check_global_limit(ip):
        return jsonify({'error': 'Free message limit reached. Wait 6 hours for reset.'}), 429
    
    # Get or initialize chat history from session
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    chat_history = session['chat_history']
    if len(chat_history) >= MAX_SESSION_MESSAGES:
        return jsonify({'error': 'Free message limit reached for this session. Start a new chat.'}), 429
    
    response = get_response(INSTRUCTIONS, chat_history, new_question)
    
    # Update chat history
    chat_history.append((new_question, response))
    session['chat_history'] = chat_history[-MAX_SESSION_MESSAGES:]
    
    # Increment global count
    increment_global_count(ip)
    
    return jsonify({'response': response})


@app.route('/limit-status', methods=['GET'])
def limit_status():
    ip = request.remote_addr
    state = load_limit_state()
    user_state = state['ips'].get(ip, {'message_count': 0, 'last_limit_time': None})
    now = datetime.now()
    cooldown_remaining = None
    if user_state['last_limit_time']:
        last_time = datetime.fromisoformat(user_state['last_limit_time'])
        remaining = timedelta(hours=COOLDOWN_HOURS) - (now - last_time)
        if remaining > timedelta(0):
            cooldown_remaining = int(remaining.total_seconds())
    return jsonify({
        'message_count': user_state['message_count'],
        'max_messages': GLOBAL_MAX_MESSAGES,
        'cooldown_remaining': cooldown_remaining
    })


@app.route('/clear', methods=['POST'])
def clear_chat():
    """Clear the chat history"""
    ip = request.remote_addr
    session['chat_history'] = []
    # Reset global limit for the current IP
    state = load_limit_state()
    if ip in state['ips']:
        state['ips'][ip] = {'message_count': 0, 'last_limit_time': None}
        save_limit_state(state)
    return jsonify({'status': 'success'})

@app.route('/restore', methods=['POST'])
def restore_chat():
    """Restore chat history for the current browser session."""
    data = request.get_json() or {}
    history = data.get('history', [])
    if not isinstance(history, list):
        return jsonify({'error': 'Invalid history format.'}), 400

    restored = []
    for item in history:
        question = item.get('question') if isinstance(item, dict) else None
        response = item.get('response') if isinstance(item, dict) else None
        if isinstance(question, str) and isinstance(response, str):
            restored.append((question, response))

    session['chat_history'] = restored[-MAX_SESSION_MESSAGES:]
    return jsonify({'status': 'restored', 'message_count': len(session['chat_history'])})

@app.route('/start', methods=['POST'])
def start():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

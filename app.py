import os
import openai
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


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/agreement')
def agreement():
    return render_template('agreement.html')

@app.route('/chat', methods=['POST'])
def chat():
    new_question = request.form['question']
    errors = get_moderation(new_question)
    if errors:
        for error in errors:
            print(error)
        # show errors on the index page
        return jsonify({'error': 'Your message was flagged by content moderation.'}), 400

    # Get or initialize chat history from session
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    chat_history = session['chat_history']
    
    response = get_response(INSTRUCTIONS, chat_history, new_question)
    
    # Update chat history
    chat_history.append((new_question, response))
    # Keep only last 10 exchanges to avoid session getting too large
    session['chat_history'] = chat_history[-10:]

    return response


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    new_question = data.get('question', '')
    errors = get_moderation(new_question)
    if errors:
        return jsonify({'errors': errors}), 400
    
    # Get or initialize chat history from session
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    chat_history = session['chat_history']
    response = get_response(INSTRUCTIONS, chat_history, new_question)
    
    # Update chat history
    chat_history.append((new_question, response))
    session['chat_history'] = chat_history[-10:]
    
    return jsonify({'response': response})


@app.route('/clear', methods=['POST'])
def clear_chat():
    """Clear the chat history"""
    session['chat_history'] = []
    return jsonify({'status': 'success'})

@app.route('/start', methods=['POST'])
def start():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

# CourseGenie

Course recommendation chatbot for Ghana Communication Technology University.
This is my final year project.

## Features

- 🤖 **AI-Powered Course Recommendations** - Uses OpenAI GPT to suggest courses based on interests and goals
- 💬 **Conversational Memory** - Remembers context across the conversation for more natural interactions
- 🎨 **Dark/Light Theme Toggle** - Switch between themes with persistent preference
- ✨ **Example Questions** - Quick-start buttons to help users get started
- ⏳ **Typing Indicators** - Visual feedback while the bot is thinking
- 🗑️ **Clear Chat** - Reset conversation at any time
- 📱 **Mobile-Responsive** - Works great on phones, tablets, and desktops
- 🔌 **REST API** - JSON endpoint (`/api/chat`) for mobile app integration
- ✅ **Comprehensive Tests** - Unit and integration tests with mocked OpenAI calls

## Quick start

1. Create and activate a virtualenv (recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1   # (PowerShell)
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Provide an OpenAI API key (optional for development / tests):

   Create a `.env` file with:

   ```plaintext
   OPENAI_API_KEY=sk-...
   SECRET_KEY=your-secret-key-for-sessions
   ```

4. Run the Flask app:

   ```powershell
   python app.py
   ```

   Visit `http://127.0.0.1:5000` in your browser.

5. Run the (local, offline) tests:

   ```powershell
   python run_tests_manual.py
   ```

## API Endpoints

- `GET /` - Home page with instructions
- `GET /agreement` - Terms and conditions
- `GET /index` - Chat interface
- `POST /chat` - Send a message (form data)
- `POST /api/chat` - Send a message (JSON API for mobile apps)
- `POST /clear` - Clear chat history

## Mobile App

See [MOBILE.md](MOBILE.md) for instructions on wrapping this web app in a native mobile app using Capacitor or native WebViews.

## Project Structure

```plaintext
CourseGenie/
├── app.py                 # Flask application and routes
├── chatbot_logic.py       # OpenAI integration and moderation
├── requirements.txt       # Python dependencies
├── test_chatbot_local.py  # Test suite with mocked OpenAI
├── run_tests_manual.py    # Test runner (works without pytest)
├── static/
│   ├── css/              # Stylesheets with theme support
│   ├── img/              # Images and logos
│   └── js/               # Client-side JavaScript
└── templates/            # HTML templates
```

## Technologies

- **Backend**: Flask (Python)
- **AI**: OpenAI GPT-3.5-turbo
- **Frontend**: Vanilla JavaScript, CSS3
- **Testing**: Custom test runner with OpenAI mocking
 

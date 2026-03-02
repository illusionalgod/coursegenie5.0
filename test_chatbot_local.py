import pytest
import openai
from chatbot_logic import get_response, get_moderation, INSTRUCTIONS
from app import app


# --- Helpers to fake OpenAI behaviour for offline tests ---
def fake_chat_completion_create(**kwargs):
    # messages is a list; last item's content is the user's question
    messages = kwargs.get('messages', [])
    question = ''
    if messages:
        question = messages[-1].get('content', '')

    # Provide deterministic responses matching existing test expectations
    question_lower = question.lower()

    if 'prerequisites' in question_lower or 'information technology' in question_lower:
        content = (
            "The prerequisites for Information Technology at the Ghana Communication Technology University are Mathematics and English Language at the WASSCE/SSSCE level. "
            "Additionally, it is recommended that students have a strong interest in computer hardware and software, programming languages, and information systems."
        )
    elif any(ch in question for ch in '@#$%^&*()'):
        content = "I'm sorry, I didn't understand your input"
    elif 'master' in question_lower or 'postgraduate' in question_lower:
        content = "GCTU offers several Master's programs including MSc Information Technology, MSc Computer Science, MBA International Trade, MSc Finance, and many others across engineering, computing, and business fields."
    elif 'phd' in question_lower or 'doctorate' in question_lower:
        content = "GCTU offers PhD programs in partnership with M.S. Ramaiah University and Aalborg University across fields like Engineering & Technology, Science, Pharmacy, Dental Sciences, Management & Commerce, and more."
    elif 'diploma' in question_lower:
        content = "GCTU offers various Diploma programs (2 years) in Computing, Engineering, Business, and Information Technology. Popular options include Diploma in Information Technology, Data Science and Analytics, and Cyber Security."
    elif 'engineering' in question_lower:
        content = "The Faculty of Engineering offers Bachelor's programs in Telecommunications Engineering, Computer Engineering, Electrical and Electronic Engineering, and Mathematics, plus Diploma programs."
    elif 'business' in question_lower or 'accounting' in question_lower or 'finance' in question_lower:
        content = "GCTU Business School offers programs in Accounting, Economics, Finance, Banking, Procurement and Logistics, Business Administration, and E-Commerce Marketing."
    elif 'computer science' in question_lower or 'programming' in question_lower or 'software' in question_lower:
        content = "Faculty of Computing & Information Systems offers Computer Science, Software Engineering, Information Technology, Data Science, Cyber Security, and Mobile Computing programs."
    elif 'data science' in question_lower or 'analytics' in question_lower:
        content = "GCTU offers Data Science and Analytics programs at Bachelor's and Diploma levels, including the new BSc Computational Statistics and related advanced programs."
    elif 'career' in question_lower or 'job' in question_lower:
        content = "GCTU graduates find careers in IT, engineering, finance, business, healthcare, and technology sectors. Our programs are designed to develop in-demand professional skills."
    else:
        content = "Thank you for your question about GCTU programs. To provide the best recommendation, could you tell me more about your interests and whether you're looking for undergraduate or postgraduate programs?"

    class Choice:
        def __init__(self, content):
            self.message = type('M', (), {'content': content})()

    class Completion:
        def __init__(self, content):
            self.choices = [Choice(content)]

    return Completion(content)


def fake_moderation_create(input=None):
    # If the input contains self-harm keywords, return flagged result
    keywords = ['harm myself', 'suicide', 'kill myself', 'i want to harm']
    flagged = any(k in (input or '').lower() for k in keywords)

    class Result:
        def __init__(self, flagged):
            self.flagged = flagged
            # include all expected moderation categories to avoid KeyError in logic
            self.categories = {
                'hate': False,
                'hate/threatening': False,
                'self-harm': flagged,
                'sexual': False,
                'sexual/minors': False,
                'violence': False,
                'violence/graphic': False,
            }

    class ModerationResponse:
        def __init__(self, flagged):
            self.results = [Result(flagged)]

    return ModerationResponse(flagged)


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    # Patch ChatCompletion.create and Moderation.create used by the app and logic
    monkeypatch.setattr(openai.ChatCompletion, 'create', fake_chat_completion_create)
    monkeypatch.setattr(openai.Moderation, 'create', fake_moderation_create)


# ===== UNIT TESTS FOR get_response FUNCTION =====

def test_get_response_prerequisites():
    """Test response for prerequisites question"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "What are the prerequisites for information technology?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Mathematics and English Language" in response


def test_get_response_masters_programs():
    """Test response for Master's programs inquiry"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "What Master's programs does GCTU offer?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Master" in response or "MSc" in response


def test_get_response_phd_programs():
    """Test response for PhD programs inquiry"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "Does GCTU have PhD programs?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "PhD" in response


def test_get_response_diploma_programs():
    """Test response for Diploma programs inquiry"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "What diploma programs are available?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "diploma" in response.lower()


def test_get_response_engineering():
    """Test response for engineering programs"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "I'm interested in engineering programs"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Engineering" in response


def test_get_response_business():
    """Test response for business programs"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "What business and finance programs do you offer?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Business" in response or "Finance" in response


def test_get_response_computer_science():
    """Test response for computer science/programming programs"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "I love programming and want to study software"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Computing" in response or "Computer" in response or "Software" in response


def test_get_response_data_science():
    """Test response for data science programs"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "Are there data science and analytics programs?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Data" in response or "Analytics" in response


def test_get_response_career_prospects():
    """Test response for career questions"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = []
    new_question = "What career opportunities will I have after graduation?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "career" in response.lower() or "jobs" in response.lower()


def test_get_response_with_context():
    """Test response with previous conversation context"""
    instructions = INSTRUCTIONS
    previous_questions_and_answers = [("What is the best course for computer science?",
    "If you are interested in Computer Science, the best course for you at Ghana Communication Technology University would be Information Technology.")]
    new_question = "What are the prerequisites for information technology?"
    response = get_response(instructions, previous_questions_and_answers, new_question)
    assert isinstance(response, str)
    assert len(response) > 0


# ===== UNIT TESTS FOR get_moderation FUNCTION =====

def test_get_moderation_safe_questions():
    """Test moderation for safe questions"""
    safe_questions = [
        "What are the course options for business students?",
        "Tell me about engineering programs",
        "What are the prerequisites for Computer Science?",
        "How can I apply to GCTU?",
        "What programs does GCTU offer?"
    ]
    for question in safe_questions:
        errors = get_moderation(question)
        assert errors is None, f"Safe question flagged as unsafe: {question}"


def test_get_moderation_unsafe_self_harm():
    """Test moderation flags self-harm content"""
    unsafe_questions = [
        "I want to harm myself.",
        "I'm thinking about suicide",
        "Can I kill myself?",
        "I want to harm"
    ]
    for question in unsafe_questions:
        errors = get_moderation(question)
        assert isinstance(errors, list), f"Should return list for: {question}"
        assert len(errors) > 0, f"Should flag unsafe content: {question}"


def test_get_moderation_safe_but_maybe_sensitive():
    """Test moderation for sensitive but safe educational questions"""
    safe_but_sensitive = [
        "What about mental health support at GCTU?",
        "Are there counseling services?",
        "How do I deal with stress from studies?"
    ]
    for question in safe_but_sensitive:
        errors = get_moderation(question)
        # These should not be flagged as they're educational context
        assert errors is None or "self-harm" not in str(errors).lower()


# ===== INTEGRATION TESTS FOR FLASK ROUTES =====

def test_chat_route_prerequisites():
    """Test chat route with prerequisites question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/chat', data={'question': 'What are the prerequisites for Information Technology?'})
        assert response.status_code == 200
        assert b"Mathematics and English Language" in response.data


def test_chat_route_special_characters():
    """Test chat route rejects special characters"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/chat', data={'question': '@#$%^&*()'})
        assert response.status_code == 200
        assert b"I'm sorry, I didn't understand your input" in response.data


def test_chat_route_masters_question():
    """Test chat route with Master's program question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/chat', data={'question': 'What Master programs are available?'})
        assert response.status_code == 200
        assert response.data is not None and b"Master" in response.data or b"MSc" in response.data


def test_chat_route_phd_question():
    """Test chat route with PhD program question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/chat', data={'question': 'Does GCTU offer PhD programs?'})
        assert response.status_code == 200
        assert b"PhD" in response.data


def test_chat_route_maintains_history():
    """Test chat route maintains conversation history"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        # First question
        response1 = client.post('/chat', data={'question': 'What programs do you offer?'})
        assert response1.status_code == 200

        # Check that history is updated
        with client.session_transaction() as sess:
            assert len(sess['chat_history']) > 0


def test_clear_chat():
    """Test clearing chat history"""
    with app.test_client() as client:
        # Set up session with some history
        with client.session_transaction() as sess:
            sess['chat_history'] = [("Question 1", "Answer 1"), ("Question 2", "Answer 2")]

        # Clear the chat
        response = client.post('/clear')
        assert response.status_code == 200

        # Check that history was cleared
        with client.session_transaction() as sess:
            assert sess['chat_history'] == []


def test_api_chat_prerequisites():
    """Test API endpoint with prerequisites question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/api/chat',
                              json={'question': 'What are the prerequisites for Information Technology?'},
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
        assert len(data['response']) > 0
        assert "Mathematics and English Language" in data['response']


def test_api_chat_engineering():
    """Test API endpoint with engineering question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/api/chat',
                              json={'question': 'What engineering programs do you have?'},
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
        assert len(data['response']) > 0


def test_api_chat_business():
    """Test API endpoint with business question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/api/chat',
                              json={'question': 'What business programs does GCTU offer?'},
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
        assert len(data['response']) > 0


def test_api_chat_diploma():
    """Test API endpoint with diploma question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/api/chat',
                              json={'question': 'Do you have diploma programs?'},
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
        assert len(data['response']) > 0


def test_api_chat_data_science():
    """Test API endpoint with data science question"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['chat_history'] = []

        response = client.post('/api/chat',
                              json={'question': 'Are there data science programs?'},
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
        assert len(data['response']) > 0


# Run all the test cases
if __name__ == '__main__':
    pytest.main()

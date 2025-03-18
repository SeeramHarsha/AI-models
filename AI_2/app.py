from flask import Flask, request, jsonify, render_template, session
import subprocess
import os
import json
import google.generativeai as genai
from werkzeug.utils import secure_filename
import shutil
import cv2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
GEMINI_API_KEY= 'AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '74G5X9B2')  # Use environment variable in production

# Configure Gemini API
print("Loaded API Key:", os.getenv("GEMINI_API_KEY"))

genai.configure(api_key="AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4")
model = genai.GenerativeModel("gemini-2.0-flash")

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '74G5X9B2')

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_chat', methods=['POST'])
def start_chat():
    if 'file' not in request.files and 'description' not in request.form:
        return jsonify({'error': 'No file or description provided'})

    file = request.files.get('file')
    description = request.form.get('description', '').strip()

    if file and file.filename:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        session['file_path'] = file_path

        # Determine file type
        if filename.endswith('.fbx'):
            session['file_type'] = '3d'
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            session['file_type'] = 'image'
        elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            session['file_type'] = 'video'
        else:
            return jsonify({'error': 'Invalid file format. Only FBX, image, or video files are allowed'})

    if description:
        session['description'] = description

    session['chat_history'] = []

    recommended_questions = generate_recommended_questions(description)

    return jsonify({'success': True, 'questions': recommended_questions})

@app.route('/chat', methods=['POST'])
def chat():
    question = request.json.get('question')
    if not question:
        return jsonify({'error': 'No question provided'})

    try:
        chat_history = session.get('chat_history', [])
        description = session.get('description', '')
        file_path = session.get('file_path', '')
        file_type = session.get('file_type', '')

        response = analyze_input(file_path, file_type, description, question, chat_history)

        chat_history.append((question, response))
        session['chat_history'] = chat_history

        return jsonify({'response': response})

    except Exception as e:
        return jsonify({'error': str(e)})

# Generate recommended questions
def generate_recommended_questions(description):
    prompt = f"""
    You are an AI that generates questions for 3D models, images, and videos. Given the following description:
    {description}

    Generate **exactly 7** 5 word simple questions that a user might ask about this content.
    Provide only the questions as a numbered list (1-7).
    """

    try:
        response = model.generate_content(prompt)

        if not response or not hasattr(response, 'text') or not response.text.strip():
            raise ValueError("Empty response from Gemini API")

        lines = response.text.strip().split("\n")
        questions = [line.split(". ", 1)[-1] for line in lines if line.strip() and line[0].isdigit()]

        return questions if len(questions) >= 7 else questions

    except Exception as e:
        print(f"Error generating recommended questions: {e}")
        return [
            "What is the purpose of this content?",
            "What key elements are present?",
            "How does this structure function?",
            "What materials are used?",
            "Is there any animation or interaction?",
            "What are the main components?",
            "Is this model compatible with 3D printing?"
        ]

def analyze_input(file_path, file_type, description, question, chat_history=None):
    if file_type == '3d':
        return run_blender_analysis(file_path, description, question, chat_history)
    elif file_type == 'image':
        return analyze_image(file_path, description, question, chat_history)
    elif file_type == 'video':
        return analyze_video(file_path, description, question, chat_history)
    else:
        return run_text_analysis(description, question, chat_history)

def run_blender_analysis(file_path, description, question, chat_history=None):
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '3d.py')
    model_folder = os.path.join(UPLOAD_FOLDER, 'temp_model')
    os.makedirs(model_folder, exist_ok=True)

    try:
        with open(os.path.join(model_folder, 'description.txt'), 'w') as f:
            f.write(description)
        shutil.copy2(file_path, os.path.join(model_folder, 'model.fbx'))

        history_context = "\n".join(f"Q: {q}\nA: {a}" for q, a in chat_history) if chat_history else ""

        prompt = f"""
        You are an AI that explains 3D models.
        Model description: {description}
        {history_context}
        Current question: {question}
        """

        result = subprocess.run([
            BLENDER_PATH, '--background', '--python', script_path, '--', model_folder, prompt, '--'
        ], capture_output=True, text=True)

        return extract_response(result.stdout)

    finally:
        shutil.rmtree(model_folder, ignore_errors=True)

def analyze_image(file_path, description, question, chat_history=None):
    return f"Analyzing image with description: {description} and question: {question}"

def analyze_video(file_path, description, question, chat_history=None):
    keyframe_path = extract_keyframe(file_path)
    if keyframe_path:
        return analyze_image(keyframe_path, description, question, chat_history)
    return "Failed to extract keyframe for analysis."

def extract_keyframe(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mid_frame = frame_count // 2  # Capture a middle frame for analysis

    cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
    success, frame = cap.read()
    if success:
        keyframe_filename = os.path.join(UPLOAD_FOLDER, "keyframe.jpg")
        cv2.imwrite(keyframe_filename, frame)
        cap.release()
        return keyframe_filename
    cap.release()
    return None

def run_text_analysis(description, question, chat_history=None):
    return f"simple Answering based on description: {description} and question: {question}"

def extract_response(output):
    lines = output.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return ' '.join(cleaned_lines) if cleaned_lines else "I couldn't process the content properly. Please try again."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

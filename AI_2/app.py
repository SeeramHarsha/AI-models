from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import base64

app = Flask(__name__)

# Configure Gemini Flash
genai.configure(api_key="AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4")
model = genai.GenerativeModel("models/gemini-1.5-flash")

# Helper to prepare input file for Gemini
def load_media(file):
    return {
        "mime_type": file.mimetype,
        "data": base64.b64encode(file.read()).decode()
    }

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    file = request.files['media']
    description = request.form['description']
    media = load_media(file)

    prompt = f"""You are a visual content educator.
Analyze the provided visual input and the concept '{description}'.
Generate 7 concise, relevant, and concept-related questions based on the visual context.
Number each question clearly and the questions 5 words.
Output format:
1. Question 1
2. Question 2
..."""

    response = model.generate_content([
        prompt,
        media
    ])

    raw_output = response.text.strip()

    # Clean and extract individual questions
    questions = [q.strip().split(". ", 1)[-1] for q in raw_output.split("\n") if q.strip()]
    return jsonify({'questions': questions})


@app.route('/answer_question', methods=['POST'])
def answer_question():
    question = request.json['question']
    description = request.json['description']
    media_data = request.json['media']
    media = {
        "mime_type": media_data['mime_type'],
        "data": media_data['data']
    }

    prompt = f"""Analyze the visual input and the concept '{description}'.
Answer the question clearly and concisely:
"{question}"."""

    response = model.generate_content([
        prompt,
        media
    ])

    # Clean response to remove excess spacing
    clean_answer = response.text.strip().replace('\n', ' ')
    return jsonify({'answer': clean_answer})


if __name__ == '__main__':
    app.run(debug=True)

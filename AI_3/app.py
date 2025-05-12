from flask import Flask, request, jsonify
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

@app.route('/generate_answers', methods=['POST'])
def generate_answers():
    data = request.form
    questions = data.getlist('questions')  # List of questions
    file = request.files['media']          # Uploaded media
    description = data['description']      # Description or concept
    
    media = load_media(file)

    # Generate answers using the model
    answers = []
    for question in questions:
        prompt = f"Analyze the concept '{description}' and answer the question: {question}"
        response = model.generate_content([prompt, media])
        answers.append({
            "question": question,
            "answer": response.text.strip()
        })

    return jsonify({'answers': answers})

if __name__ == '__main__':
    app.run(debug=True)

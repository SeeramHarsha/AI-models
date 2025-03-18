from flask import Flask, render_template, request
import google.generativeai as genai
import random

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key="AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4")
model = genai.GenerativeModel("gemini-2.0-flash")

def get_short_answers(questions):
    responses = []
    for q in questions:
        try:
            prompt = f"You are an Ai model that answers the questions generated from the image you need to give the answers briefly and make 3 of the questions mcqs give answers with questions:\n{q}"
            response = model.generate_content(prompt)
            answer = response.text.strip() if response and hasattr(response, 'text') else "No valid response from Gemini."
        except Exception as e:
            answer = "Error processing the question."
        responses.append(answer)
    return responses

def generate_mcqs(questions, answers):
    mcqs = []
    for q, ans in zip(questions, answers):
        options = [ans, "Option 1", "Option 2", "Option 3"]
        random.shuffle(options)
        mcqs.append({"question": q, "options": options, "answer": ans})
    return mcqs

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        questions = request.form.getlist('questions')
        answers = get_short_answers(questions)
        mcq_questions = questions[:3]
        mcq_answers = answers[:3]
        direct_questions = questions[3:]
        direct_answers = answers[3:]
        mcqs = generate_mcqs(mcq_questions, mcq_answers)
        return render_template('result.html', mcqs=mcqs, direct_qas=zip(direct_questions, direct_answers))
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

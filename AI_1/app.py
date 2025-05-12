import os
import mimetypes
import cv2
from flask import Flask, request, jsonify
from PIL import Image
import google.generativeai as genai

# Setup
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
genai.configure(api_key="AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4")
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

# Helpers
def load_image(path):
    return Image.open(path)

def extract_key_frames(video_path, num_frames=5):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total_frames // num_frames)
    frames = []

    for i in range(num_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(UPLOAD_FOLDER, f"frame_{i}.jpg")
            cv2.imwrite(frame_path, frame)
            frames.append(Image.open(frame_path))

    cap.release()
    return frames

def generate_questions(visuals, concept):
    prompt = f"""
You are an intelligent tutor AI.

Analyze the visual input carefully and combine that understanding with the given concept: "{concept}"

Then generate 5 simple questions relevant that relate the concept to the visual scene and 3 in 7 should be mcqs.

Each question should reflect how the concept can be applied or understood in the context of what is seen in the image/video.
"""
    response = model.generate_content([prompt] + visuals)
    return response.text.strip()

# Routes
@app.route("/generate-questions", methods=["POST"])
def generate_questions_endpoint():
    file = request.files.get("file")
    concept = request.form.get("concept")

    if not file or not concept:
        return jsonify({"error": "File and concept are required"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("image"):
        visuals = [load_image(file_path)]
    elif mime_type and mime_type.startswith("video"):
        visuals = extract_key_frames(file_path)
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    questions = generate_questions(visuals, concept)
    return jsonify({"questions": questions})

# Optional: simple health check for browser access
@app.route("/", methods=["GET"])
def health_check():
    return "API is running. Use POST /generate-questions with 'file' and 'concept'."

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import cv2
import torch
import os
from PIL import Image
import google.generativeai as genai

os.environ["HF_HOME"] = "/tmp/huggingface"

from transformers import BlipProcessor, BlipForConditionalGeneration

# Flask app setup
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Gemini API (Use your API key)
API_KEY = "AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4"  # Replace with your actual API key
genai.configure(api_key=API_KEY)

# Load BLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large").to(device)

# Function to get available Gemini model
def get_gemini_model():
    try:
        models = genai.list_models()
        available_models = [model.name for model in models]
        print("Available Gemini models:", available_models)

        for model in [
            "models/gemini-1.5-pro-latest",
            "models/gemini-1.5-pro-002",
            "models/gemini-2.0-pro-exp",
        ]:
            if model in available_models:
                return model
        raise ValueError("No suitable Gemini model found.")
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        return None

# Get the correct Gemini model
GEMINI_MODEL = get_gemini_model()

def extract_frame_from_video(video_path):
    """Extracts the middle frame from a video for processing."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    middle_frame_idx = frame_count // 2  # Take the middle frame

    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
    ret, frame = cap.read()
    cap.release()

    return frame if ret else None

def generate_caption(image):
    """Generates a description for an image using BLIP."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image)
    inputs = processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        output = model.generate(**inputs)
    
    caption = processor.tokenizer.decode(output[0], skip_special_tokens=True)
    return caption

def generate_questions(description, topic):
    """Generate questions based on the image description and user-given topic."""
    if not description.strip() or not topic.strip():
        return "⚠️ Description or topic missing. Cannot generate questions."

    if not GEMINI_MODEL:
        return "⚠️ No valid Gemini model found. Cannot generate questions."

    prompt = f"Based on the following description: '{description}', generate 7 questions  related to {topic}."
    
    try:
        gen_model = genai.GenerativeModel(GEMINI_MODEL)
        response = gen_model.generate_content(prompt)
        return response.text.strip() if response.text else "⚠️ No questions generated."
    except Exception as e:
        return f"Error generating questions: {str(e)}"


@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Chatbot endpoint that takes an image or video and topic, and generates questions."""
    if 'file' not in request.files or 'topic' not in request.form:
        return jsonify({"error": "Image/Video and topic are required."}), 400

    file = request.files['file']
    topic = request.form['topic']
    
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Check file type
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension in ['jpg', 'jpeg', 'png']:
        image = cv2.imread(filepath)  # Directly read the image
    elif file_extension in ['mp4', 'avi', 'mov', 'mkv']:
        image = extract_frame_from_video(filepath)  # Extract frame from video
        if image is None:
            return jsonify({"error": "Could not extract frame from video."}), 400
    else:
        return jsonify({"error": "Unsupported file type. Upload an image or video."}), 400

    caption = generate_caption(image)
    qna = generate_questions(caption, topic)

    os.remove(filepath)  # Clean up uploaded file

    return jsonify({
        "questions": qna
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)

import bpy
import os
import json
import sys
import re

sys.path.append(r"C:\Users\seera\AppData\Roaming\Python\Python311\site-packages")

import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyAtZdcm9nN--eMNlWoiF0wRuTwE70mBkV4")
model = genai.GenerativeModel("gemini-2.0-flash")

# Analyze 3D model in Blender
def analyze_3d_model():
    analysis_data = {
        "mesh_count": 0,
        "vertex_count": 0,
        "material_count": 0,
        "has_animation": False,
    }

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            analysis_data["mesh_count"] += 1
            analysis_data["vertex_count"] += len(obj.data.vertices)
            analysis_data["material_count"] += len(obj.data.materials) if obj.data.materials else 0
            if obj.animation_data:
                analysis_data["has_animation"] = True

    return analysis_data

# Read model description
def read_model_description(folder_path):
    description_file = os.path.join(folder_path, "description.txt")
    if os.path.exists(description_file):
        with open(description_file, "r") as f:
            return f.read()
    return "No description available."

# Ask Gemini
def ask_gemini(question, analysis_data, model_description, chat_history):
    model_prompt = f"""
    You are an AI that explains 3D mechanical models.
    Given this model analysis:
    {json.dumps(analysis_data, indent=4)}
    
    Model Description:
    {model_description}
    
    Chat History:
    {chat_history}
    
    Answer in a clear and simple way:
    
    Q: {question}
    """

    try:
        response = model.generate_content(model_prompt)
        return response.text.strip() if response and hasattr(response, 'text') else "Gemini API did not return a valid response."
    except Exception as e:
        return "I encountered an error while processing your question."

# Main execution
def main():
    if "--" not in sys.argv:
        print("Error: Missing '--' separator in command-line arguments.", file=sys.stderr)
        sys.exit(1)

    argv = sys.argv[sys.argv.index("--") + 1:]
    if len(argv) < 2:
        print("Error: Missing arguments (folder_path and question)", file=sys.stderr)
        sys.exit(1)

    folder_path = argv[0]
    question = argv[1]

    chat_history = argv[2] if len(argv) > 2 else ""

    # Suppress Blender system logs
    sys.stdout = open(os.devnull, 'w')  # Redirect stdout
    sys.stderr = open(os.devnull, 'w')  # Redirect stderr

    fbx_file = next((os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".fbx")), None)
    if not fbx_file:
        print("Error: No FBX file found in the folder.", file=sys.stderr)
        sys.exit(1)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.use_relative_paths = False  # Prevent relative path issues

    try:
        bpy.ops.import_scene.fbx(filepath=fbx_file)
        analysis_results = analyze_3d_model()
    except Exception as e:
        print(f"Error loading FBX: {e}", file=sys.stderr)
        sys.exit(1)

    sys.stdout = sys.__stdout__  # Restore stdout
    sys.stderr = sys.__stderr__  # Restore stderr

    model_description = read_model_description(folder_path)
    answer = ask_gemini(question, analysis_results, model_description, chat_history)

    # ✅ Filter out any system-generated Blender logs
    clean_answer = re.sub(r"Blender.*?quit", "", answer, flags=re.DOTALL).strip()

    print(clean_answer)

if __name__ == "__main__":
    main()

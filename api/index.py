from flask import Flask, request, jsonify
import os
import base64
import io
from PIL import Image
from google import genai
from google.genai import types

app = Flask(__name__)

# This tells Vercel: "If someone sends a POST to /api, run this function"
@app.route('/api', methods=['POST'])
def proxy_handler():
    # 1. SECURITY CHECK
    server_secret = os.environ.get("PROXY_SECRET")
    client_secret = request.headers.get("Authorization")

    if server_secret and client_secret != server_secret:
        return jsonify({"error": "Forbidden: Wrong Proxy Password"}), 403

    # 2. Setup Google Client
    google_key = os.environ.get("GOOGLE_API_KEY")
    if not google_key:
        return jsonify({"error": "Server config error: GOOGLE_API_KEY missing"}), 500

    client = genai.Client(api_key=google_key)

    # 3. Parse Data (Flask makes this easy)
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    mode = data.get("mode", "text")
    prompt = data.get("prompt", "")
    input_images_b64 = data.get("images", [])

    try:
        # PREPARE CONTENT
        contents = [prompt]
        
        # Decode Images
        for b64_str in input_images_b64:
            try:
                img_data = base64.b64decode(b64_str)
                img = Image.open(io.BytesIO(img_data))
                contents.append(img)
            except Exception as e:
                print(f"Image decode error: {e}")

        # CALL GOOGLE
        if mode == "text":
            # TEXT GEN
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=contents
            )
            return jsonify({"result": response.text, "type": "text"})
        
        elif mode == "image":
            # IMAGE GEN
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"])
            )
            
            # Encode response image to Base64
            generated_img = response.candidates[0].content.parts[0].as_image()
            buffered = io.BytesIO()
            generated_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            return jsonify({"result": img_str, "type": "image"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# This is required for Vercel to find the app
if __name__ == '__main__':
    app.run()

from flask import Flask, request, jsonify
import os
import base64
import io
from PIL import Image
from google import genai

app = Flask(__name__)

@app.route('/api', methods=['POST'])
def proxy_handler():
    try:
        # 1. SECURITY CHECK
        server_secret = os.environ.get("PROXY_SECRET")
        client_secret = request.headers.get("Authorization")
        if server_secret and client_secret != server_secret:
            return jsonify({"error": "Forbidden: Wrong Proxy Password"}), 403

        # 2. Parse Data
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        mode = data.get("mode", "text")
        prompt = data.get("prompt", "")
        input_images_b64 = data.get("images", [])

        # 3. Setup Google Client (Using Vercel's Env Variable)
        google_key = os.environ.get("GOOGLE_API_KEY")
        if not google_key:
            return jsonify({"error": "Server missing GOOGLE_API_KEY"}), 500
        client = genai.Client(api_key=google_key)

        # 4. TEXT MODE (The only thing this proxy does now!)
        if mode == "text":
            # Prepare contents: [Prompt, Image1, Image2, ...]
            contents = [prompt]
            
            # Decode images to send as context to the Text AI
            for b64 in input_images_b64:
                try:
                    img_bytes = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(img_bytes))
                    contents.append(img)
                except Exception as e:
                    print(f"Image decode error: {e}")

            # Call Gemini Flash (Text Model)
            response = client.models.generate_content(
                model="gemini-flash-latest", 
                contents=contents
            )
            return jsonify({"result": response.text, "type": "text"})

        else:
            return jsonify({"error": f"This proxy is configured for TEXT mode only. Images are handled locally."}), 400

    except Exception as e:
        return jsonify({"error": f"INTERNAL SERVER ERROR: {str(e)}"}), 500

if __name__ == "__main__":
    app.run()

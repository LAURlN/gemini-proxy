from flask import Flask, request, jsonify
import os
import base64
import io
import requests
import random
from PIL import Image
from google import genai
from google.genai import types

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

        # 3. TEXT MODE -> Google (Free Tier)
        if mode == "text":
            google_key = os.environ.get("GOOGLE_API_KEY")
            if not google_key:
                return jsonify({"error": "Server missing GOOGLE_API_KEY"}), 500

            client = genai.Client(api_key=google_key)
            
            # Prepare contents (Text + Images)
            contents = [prompt]
            for b64 in input_images_b64:
                try:
                    img_bytes = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(img_bytes))
                    contents.append(img)
                except:
                    pass

            # UPDATED MODEL NAME HERE:
            response = client.models.generate_content(
                model="gemini-flash-latest", 
                contents=contents
            )
            return jsonify({"result": response.text, "type": "text"})

        # 4. IMAGE MODE -> Pollinations.ai (Free, No Auth)
        elif mode == "image":
            # Enhance prompt for pixel art
            enhanced_prompt = f"pixel art pokemon sprite, {prompt}, white background, gameboy advance style, high quality"
            
            # Add seed for randomness
            seed = random.randint(0, 999999)
            # Using FLUX model via Pollinations
            pollinations_url = f"https://image.pollinations.ai/prompt/{enhanced_prompt}?width=512&height=512&seed={seed}&model=flux&nologo=true"

            resp = requests.get(pollinations_url, timeout=60)
            if resp.status_code != 200:
                return jsonify({"error": f"Pollinations Error: {resp.text}"}), 500

            img_b64 = base64.b64encode(resp.content).decode("utf-8")
            return jsonify({"result": img_b64, "type": "image"})

        else:
            return jsonify({"error": f"Unknown mode: {mode}"}), 400

    except Exception as e:
        return jsonify({"error": f"INTERNAL PYTHON ERROR: {str(e)}"}), 500

if __name__ == '__main__':
    app.run()

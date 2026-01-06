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

# CONFIG: Updated URL for 2026
HF_MODEL_URL = "https://router.huggingface.co/models/black-forest-labs/FLUX.1-schnell"

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

        # 3. TEXT MODE -> Google Gemini (Free)
        if mode == "text":
            google_key = os.environ.get("GOOGLE_API_KEY")
            if not google_key:
                return jsonify({"error": "Server missing GOOGLE_API_KEY"}), 500

            client = genai.Client(api_key=google_key)
            
            contents = [prompt]
            for b64 in input_images_b64:
                try:
                    img_bytes = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(img_bytes))
                    contents.append(img)
                except:
                    pass

            response = client.models.generate_content(
                model="gemini-flash-latest", 
                contents=contents
            )
            return jsonify({"result": response.text, "type": "text"})

        # 4. IMAGE MODE -> Hugging Face (FLUX.1-schnell)
        elif mode == "image":
            hf_token = os.environ.get("HF_API_TOKEN")
            if not hf_token:
                return jsonify({"error": "Server missing HF_API_TOKEN"}), 500

            # Enhance prompt for Pokemon Pixel Art
            enhanced_prompt = f"pixel art pokemon sprite, {prompt}, white background, gameboy advance style, clean lines, high quality, sprite sheet aesthetic"
            
            headers = {"Authorization": f"Bearer {hf_token}"}
            payload = {"inputs": enhanced_prompt}

            # Call Hugging Face API (New Router URL)
            resp = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=50)

            if resp.status_code != 200:
                # Handle "Model Loading" error (Cold Start)
                if "loading" in resp.text.lower():
                    return jsonify({"error": "HF Model is loading (Cold Start). Please wait 30s and try again."}), 503
                return jsonify({"error": f"HuggingFace Error: {resp.text}"}), 500

            # HF returns raw binary image bytes
            img_bytes = resp.content
            
            # Convert to Base64
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            return jsonify({"result": img_b64, "type": "image"})

        else:
            return jsonify({"error": f"Unknown mode: {mode}"}), 400

    except Exception as e:
        return jsonify({"error": f"INTERNAL ERROR: {str(e)}"}), 500

if __name__ == "__main__":
    app.run()

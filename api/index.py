from flask import Flask, request, jsonify
import os
import base64
import io
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

        # 3. Setup Client (Uses your NEW Paid Key from Vercel Env)
        google_key = os.environ.get("GOOGLE_API_KEY")
        if not google_key:
            return jsonify({"error": "Server missing GOOGLE_API_KEY"}), 500
        client = genai.Client(api_key=google_key)

        # 4. TEXT MODE (Stats, Dex)
        if mode == "text":
            contents = [prompt]
            # Decode reference images if sent
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

        # 5. IMAGE MODE (Fusion - Nano Banana)
        elif mode == "image":
            contents = []
            # Decode Parent Sprites (Crucial for Fusion!)
            for b64 in input_images_b64:
                try:
                    img_bytes = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(img_bytes))
                    contents.append(img)
                except Exception as e:
                    print(f"Image decode error: {e}")

            contents.append(prompt)

            # CALL GEMINI 2.5 FLASH IMAGE (The Paid Model)
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"])
            )
            
            # Extract Image
            generated_img = response.candidates[0].content.parts[0].as_image()
            
            # Convert to Base64
            buffered = io.BytesIO()
            generated_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            return jsonify({"result": img_str, "type": "image"})

        else:
            return jsonify({"error": f"Unknown mode: {mode}"}), 400

    except Exception as e:
        return jsonify({"error": f"INTERNAL SERVER ERROR: {str(e)}"}), 500

if __name__ == "__main__":
    app.run()

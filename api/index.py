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
    # 1. SECURITY CHECK
    server_secret = os.environ.get("PROXY_SECRET")
    client_secret = request.headers.get("Authorization")
    if server_secret and client_secret != server_secret:
        return jsonify({"error": "Forbidden: Wrong Proxy Password"}), 403

    # 2. Parse Data
    data = request.json
    mode = data.get("mode", "text")
    prompt = data.get("prompt", "")
    
    # Note: We ignore input_images for image mode now, as Pollinations is Text-to-Image
    input_images_b64 = data.get("images", [])

    try:
        # 3. TEXT MODE -> Use Google (Free)
        if mode == "text":
            google_key = os.environ.get("GOOGLE_API_KEY")
            client = genai.Client(api_key=google_key)
            
            # Prepare images for Google (Text mode still supports image input!)
            contents = [prompt]
            for b64 in input_images_b64:
                try:
                    img = Image.open(io.BytesIO(base64.b64decode(b64)))
                    contents.append(img)
                except:
                    pass

            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=contents
            )
            return jsonify({"result": response.text, "type": "text"})

        # 4. IMAGE MODE -> Use Pollinations.ai (Free, No Key)
        elif mode == "image":
            # We enhance the prompt to ensure pixel art style since we lost the reference images
            enhanced_prompt = f"pixel art pokemon sprite, {prompt}, solid green background, gameboy advance style, high quality, sprite sheet style"
            
            # Pollinations URL hack (it accepts prompts via URL)
            # We add a random seed to ensure different results each time
            seed = random.randint(0, 999999)
            pollinations_url = f"https://image.pollinations.ai/prompt/{enhanced_prompt}?width=512&height=512&seed={seed}&model=flux&nologo=true"

            # Fetch the image
            resp = requests.get(pollinations_url, timeout=60)

            if resp.status_code != 200:
                return jsonify({"error": f"Pollinations Error: {resp.text}"}), 500

            # Convert raw bytes to Base64 to send back to you
            img_b64 = base64.b64encode(resp.content).decode("utf-8")
            
            return jsonify({"result": img_b64, "type": "image"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()

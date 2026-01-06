from flask import Flask, request, jsonify
import os
import base64
import io
import requests
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

        # Setup Google Client
        google_key = os.environ.get("GOOGLE_API_KEY")
        if not google_key:
            return jsonify({"error": "Server missing GOOGLE_API_KEY"}), 500
        client = genai.Client(api_key=google_key)

        # 3. TEXT MODE -> Gemini Flash (Free)
        if mode == "text":
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

        # 4. IMAGE MODE -> Google Imagen (Trying for Free Tier)
        elif mode == "image":
            # Note: Imagen is Text-to-Image only. It ignores reference images.
            # We enhance the prompt to ensure pixel art style.
            enhanced_prompt = f"pixel art pokemon sprite, {prompt}, white background, gameboy advance style, high quality sprite"

            try:
                # Using the standard Imagen 3 Fast model
                # If you specifically have access to 'imagen-4.0', change the string below.
                response = client.models.generate_images(
                    model='imagen-3.0-generate-001', 
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                    )
                )
                
                # Extract Image
                generated_image = response.generated_images[0].image
                
                # Convert to Base64 to send back to Germany
                buffered = io.BytesIO()
                generated_image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                return jsonify({"result": img_str, "type": "image"})
                
            except Exception as e:
                # Capture the specific Google API error (like Limit 0)
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    return jsonify({"error": "QUOTA_ERROR: Imagen is not free on this account. Try Pollinations again?"}), 500
                return jsonify({"error": f"Google Imagen Error: {error_msg}"}), 500

        else:
            return jsonify({"error": f"Unknown mode: {mode}"}), 400

    except Exception as e:
        return jsonify({"error": f"INTERNAL PYTHON ERROR: {str(e)}"}), 500

if __name__ == "__main__":
    app.run()

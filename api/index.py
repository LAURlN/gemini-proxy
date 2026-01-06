from http.server import BaseHTTPRequestHandler
import json
import os
import base64
import io
from PIL import Image
from google import genai
from google.genai import types

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. SECURITY CHECK
        server_secret = os.environ.get("PROXY_SECRET")
        client_secret = self.headers.get("Authorization")

        if server_secret and client_secret != server_secret:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: Wrong Proxy Password")
            return

        # 2. Parse Incoming JSON
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: Bad JSON")
            return

        # 3. Setup Google Client
        google_key = os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=google_key)

        # 4. Handle Request Modes
        mode = body.get("mode", "text")
        prompt = body.get("prompt", "")
        input_images_b64 = body.get("images", []) # List of base64 strings

        try:
            # PREPARE CONTENT (Text + Images)
            contents = [prompt]
            
            # Convert incoming Base64 strings back to PIL Images for Google
            for b64_str in input_images_b64:
                img_data = base64.b64decode(b64_str)
                img = Image.open(io.BytesIO(img_data))
                contents.append(img)

            if mode == "text":
                # TEXT GEN (Stats, Dex)
                response = client.models.generate_content(
                    model="gemini-1.5-flash", # Or gemini-flash-latest
                    contents=contents
                )
                output = {"result": response.text, "type": "text"}
            
            elif mode == "image":
                # IMAGE GEN (Fusion)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=contents,
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"])
                )
                
                # Extract Image and Convert to Base64 to send back to Germany
                generated_img = response.candidates[0].content.parts[0].as_image()
                buffered = io.BytesIO()
                generated_img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

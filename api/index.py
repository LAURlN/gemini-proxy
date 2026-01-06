from http.server import BaseHTTPRequestHandler
import json
import os
from google import genai

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Parse the incoming request (from your PC)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data.decode('utf-8'))
        
        # 2. Get the Prompt and API Key
        user_prompt = body.get("prompt", "Hello!")
        # We will set this environment variable in the Vercel Dashboard later
        api_key = os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Error: GOOGLE_API_KEY not set in Vercel.")
            return

        # 3. Call Google Gemini (Text Model)
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash", # Fast model for testing
                contents=user_prompt
            )
            result_text = response.text

            # 4. Send response back to Germany
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_data = {"status": "success", "reply": result_text}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

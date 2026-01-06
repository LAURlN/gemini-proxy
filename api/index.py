from http.server import BaseHTTPRequestHandler
import json
import os
from google import genai

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. SECURITY CHECK
        # We check if the incoming request has the correct password header
        server_secret = os.environ.get("PROXY_SECRET")
        client_secret = self.headers.get("Authorization")

        if server_secret and client_secret != server_secret:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: Wrong Proxy Password")
            return

        # 2. Parse Incoming Request
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: Bad JSON")
            return

        # 3. Get Google API Key from Vercel Environment
        google_key = os.environ.get("GOOGLE_API_KEY")
        if not google_key:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Error: GOOGLE_API_KEY not set in Vercel")
            return

        # 4. Handle The Request (Text or Image?)
        # We look for a 'mode' in the body to decide what to do
        mode = body.get("mode", "text")
        prompt = body.get("prompt", "")
        
        client = genai.Client(api_key=google_key)

        try:
            if mode == "text":
                # Text Generation (Gemini 2.0 Flash)
                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    contents=prompt
                )
                output = {"result": response.text}
            
            else:
                # Placeholder for Image logic (we will add this next!)
                output = {"result": "Image mode not implemented yet"}

            # 5. Send Result Back
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(output).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.wfile.write(str(e).encode('utf-8'))

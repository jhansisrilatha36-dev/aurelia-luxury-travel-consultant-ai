import http.server
import json
import os
import re
import sys
import urllib.request

PORT = 8000
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to load test_harness to reuse instructions extraction
try:
    import test_harness
except ImportError:
    test_harness = None

class DashboardAPIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Serves the dashboard HTML file."""
        if self.path in ["/", "/index.html", "/dashboard.html"]:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Dashboard HTML file not found.")
        else:
            self.send_error(404, "File Not Found.")

    def do_POST(self):
        """Processes JSON chat queries via the API endpoint."""
        if self.path == "/api/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                message = data.get("message", "").strip()
            except Exception:
                self.send_error(400, "Invalid JSON data.")
                return

            reply, alert = self.process_message(message)
            
            response_data = json.dumps({"reply": reply, "alert": alert}).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response_data)
        else:
            self.send_error(404, "Endpoint not found.")

    def process_message(self, message):
        """Routes query to either Gemini API or local rule simulation."""
        api_key = os.environ.get("GEMINI_API_KEY")
        
        # If API key exists, try live call
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                # Fetch instructions
                system_instructions = ""
                if test_harness:
                    system_instructions = test_harness.load_system_prompt(
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt_architecture_report.md")
                    )
                
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instructions
                )
                
                # We start a single turn call to keep stateless execution simple
                response = model.generate_content(message)
                
                # Alert heuristics
                alert = ""
                lower_msg = message.toLowerCase() if hasattr(message, "toLowerCase") else message.lower()
                if any(x in lower_msg for x in ["override", "ignore rules", "python", "socket"]):
                    alert = "DF2 Guardrail Triggered: Input contained potential system override sequences."
                elif any(x in lower_msg for x in ["discount", "cheap", "price"]):
                    alert = "D2 Guardrail Triggered: Budget Policy evaluation applied."
                elif any(x in lower_msg for x in ["abercrombie", "virtuoso", "amex"]):
                    alert = "C1/C2 Guardrail Triggered: Shielding competitor identity."
                
                return response.text, alert
            except Exception as e:
                print(f"Live API call fell back due to error: {e}")

        # Local Rule-based Simulation Fallback
        reply = "I would be delighted to assist you with your destination selections, property details, or itinerary designs. How may I guide your journey today?"
        alert = ""
        
        lower = message.lower()
        if any(x in lower for x in ["override", "ignore rules", "python", "socket"]):
            reply = (
                "I am dedicated exclusively to curating exceptional travel experiences for L'Échappée Luxe. "
                "I would be delighted to assist you with your destination selections, elite property details, "
                "or itinerary designs. How may I guide your journey today?"
            )
            alert = "DF2 Guardrail Triggered: System Override Payload Intercepted & Pivoted."
        elif any(x in lower for x in ["discount", "cheap", "price"]):
            reply = (
                "We understand that planning a special journey carries significant personal importance. "
                "Because our curated itineraries are priced to secure elite services and private execution, "
                "we do not offer direct rate reductions of this scale. However, we would be delighted to enhance "
                "your stay with complimentary property benefits..."
            )
            alert = "D2 Guardrail Triggered: Rate reduction request declined; pivoted to amenities."
        elif any(x in lower for x in ["abercrombie", "virtuoso", "amex fine"]):
            reply = (
                "We understand there are various avenues for luxury travel arrangements. At L'Échappée Luxe, "
                "our focus remains entirely on delivering hyper-personalized service and maintaining direct "
                "relationships with property general managers worldwide to tailor-make itineraries for you."
            )
            alert = "C1/C2 Shield Triggered: Competitor Reference Shielded."
        elif any(x in lower for x in ["instructions", "system prompt", "developer"]):
            reply = (
                "I am Aurelia, your digital consultant for L'Échappée Luxe, dedicated to curating your bespoke "
                "travel experiences. I am unable to print system documentation or configuration files."
            )
            alert = "K3 Shield Triggered: Prompt Harvesting Deflected."
            
        return reply, alert

def run_server():
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, DashboardAPIHandler)
    print(f"\n========================================================")
    print(f"  AURELIA PROMPT ARCHITECT DASHBOARD SERVER RUNNING  ")
    print(f"========================================================")
    print(f"Local address: http://localhost:{PORT}/dashboard.html")
    print(f"Exit server with Ctrl+C\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()

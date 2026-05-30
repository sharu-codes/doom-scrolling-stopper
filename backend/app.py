import sys
import traceback
print("Starting app.py...", flush=True)

# Flask web server that receives webcam frames and returns detection results
import os
print("Python version:", sys.version, flush=True)

try:
    from flask import Flask, request, jsonify # Flask: web framework
    from flask_cors import CORS # Flask-CORS: allows browser to talk to this server
    print("Flask imported OK", flush=True)
    from detector import analyze_frame # import our detection logic
    print("Detector imported OK", flush=True)
except Exception as e:
    print("DETECTOR IMPORT FAILED:", e, flush=True)
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    sys.exit(1) # exit the program if imports fail
    
app = Flask(__name__) # create Flask app

# allows the frontend (running on a different port) to call this server
# without CORS, the browser blocks requets between different ports for security reasons
CORS(app)

# ––––––––– health check route –––––––––
# visit http://localhost:5000/ in your browser to confirm server is running
@app.route('/')
def index():
    return "Doomscrolling Stop – backend running!"

# ––––––––– frame analysis route –––––––––
# The browser POST requests webcam frames to this URL every 500ms.
@app.route('/analyze', methods=['POST'])
def analyze():
    if 'frame' not in request.files:
        return jsonify({'error': 'No frame uploaded', 'alarm': False}), 400
    
    frame_file = request.files['frame'] # get the uploaded file
    frame_bytes = frame_file.read() # read the file as bytes

    result = analyze_frame(frame_bytes) # run our detection logic on the frame bytes
    return jsonify(result) # return the result as JSON to the browser

# ––––––––– start server –––––––––
# debug=True → auto-restarts server when you save code changes
# host='0.0.0.0' → accessible from any device on your network
# port=5000 → server runs at http://localhost:5000
port = int(os.environ.get('PORT', 5000)) # Use PORT env var if set (for deployment), otherwise default to 5000
app.run(host='0.0.0.0', port=port)
if __name__ == '__main__':
    pass
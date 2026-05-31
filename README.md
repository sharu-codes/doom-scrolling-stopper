> Real-time habit-interruption tool using computer vision.
> Catches you doomscrolling and triggers an alarm.

## 🌐 Live Demo
https://sharu-codes.github.io/doom-scrolling-stop

## ⚙️ How It Works
1. Your browser streams webcam frames every 500ms
2. Python backend runs Google MediaPipe on each frame
3. Detects head pitch (solvePnP) + iris position (eye gaze)
4. Triggers alarm.wav when doomscrolling posture detected
5. Works even in background browser tabs

## 🛠️ Tech Stack
| Layer    | Tech                              |
|----------|-----------------------------------|
| Backend  | Python, Flask, MediaPipe, OpenCV  |
| Frontend | HTML, Tailwind CSS, JavaScript    |
| Design   | Google Stitch (AI UI generator)   |
| Hosting  | Render.com + GitHub Pages         |

## 🚀 Run Locally
```
pip install flask flask-cors opencv-python mediapipe numpy
python backend/app.py
# Open frontend/index.html with Live Server
```

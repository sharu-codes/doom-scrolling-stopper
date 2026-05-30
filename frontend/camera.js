// camera.js — Webcam capture + backend communication + UI updates

// ── Configuration ─────────────────────────────────────────────────────────
const BACKEND_URL = 'http://localhost:5000/analyze';    // Where to send frames
const FRAME_INTERVAL_MS = 500;      // How often to analyze (every 500ms = 2 fps)
const ALARM_THRESHOLD = 2;          // How many consecutive "alarm" results before sound plays
const SAFE_THRESHOLD = 4;           // How many consecutive "safe" results before sound stops

// ── State Variables ───────────────────────────────────────────────────────
let videoStream = null;             // Holds the webcam stream object
let analyzeInterval = null;         // Holds the setInterval timer
let consecutiveAlarms = 0;          // Counter for alarm streak
let consecutiveSafe = 0;            // Counter for safe streak
let totalAlarmCount = 0;            // Total times alarm triggered this session
let sessionStartTime = null;        // When the session started

// ── DOM References ────────────────────────────────────────────────────────
// Get references to HTML elements we'll update with JS
const video         = document.getElementById('webcamVideo');
const canvas        = document.getElementById('captureCanvas');
const ctx           = canvas.getContext('2d');  // 2D drawing context on canvas
const alarmOverlay  = document.getElementById('alarmOverlay');
const statusPill    = document.getElementById('statusPill');
const statusBlock   = document.getElementById('statusBlock');
const statusIcon    = document.getElementById('statusIcon');
const statusText    = document.getElementById('statusText');
const pitchVal      = document.getElementById('pitchVal');
const irisVal       = document.getElementById('irisVal');
const alarmCount    = document.getElementById('alarmCount');
const sessionTime   = document.getElementById('sessionTime');
const logList       = document.getElementById('logList');
const startBtn      = document.getElementById('startBtn');
const stopBtn       = document.getElementById('stopBtn');

// ── startCamera(): Request webcam access and begin analysis ───────────────
async function startCamera() {
    try {
        // Ask browser permission to use the camera.
        // video: { facingMode: 'user' } = front-facing camera
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: 640, height: 480 }
        });

        video.srcObject = videoStream;  // Connect stream to <video> element

        // Wait for video to be ready before starting analysis
        video.onloadedmetadata = () => {
            // Set canvas to same size as video (needed for frame capture)
            canvas.width  = video.videoWidth;
            canvas.height = video.videoHeight;

            // Start analyzing frames on a timer
            analyzeInterval = setInterval(sendFrame, FRAME_INTERVAL_MS);

            // Start session timer
            sessionStartTime = Date.now();
            setInterval(updateSessionTime, 1000);   // Update time display every second

            addLog('Camera started. Analyzing...', 'safe-log');
        };

        // Update button states
        startBtn.disabled = true;
        stopBtn.disabled  = false;

    } catch (err) {
        // Common error: user denied camera permission
        addLog('Camera access denied. Please allow camera in browser settings.', 'alarm-log');
        console.error('Camera error:', err);
    }
}

// ── stopCamera(): Turn off webcam and stop analysis ───────────────────────
function stopCamera() {
    // Stop all video tracks (releases camera hardware)
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }

    // Clear the analysis timer
    if (analyzeInterval) {
        clearInterval(analyzeInterval);
        analyzeInterval = null;
    }

    stopAlarm();                // Stop any playing alarm
    setUIState('idle');         // Reset UI

    startBtn.disabled = false;
    stopBtn.disabled  = true;

    addLog('Camera stopped.', '');
}

// ── sendFrame(): Capture one frame and send to backend ────────────────────
async function sendFrame() {
    // Draw current video frame onto hidden canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to JPEG blob (compressed image data)
    // Quality 0.8 = 80% quality — good balance of accuracy and speed
    canvas.toBlob(async (blob) => {
        if (!blob) return;  // Skip if capture failed

        // Build a FormData object — like an HTML form file upload
        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');    // Key must match backend's request.files['frame']

        try {
            // POST the frame to our Python backend
            const response = await fetch(BACKEND_URL, {
                method: 'POST',
                body: formData
                // No Content-Type header — browser sets it automatically with boundary for FormData
            });

            if (!response.ok) return;   // Skip on HTTP errors

            const data = await response.json();  // Parse JSON response
            handleResult(data);                  // Update UI and alarm

        } catch (err) {
            // Network error — backend might not be running
            updateStatus('no_face', { status: 'Backend offline' });
        }
    }, 'image/jpeg', 0.8);
}

// ── handleResult(): Process backend response ──────────────────────────────
function handleResult(data) {
    // Update the pitch and iris readouts
    pitchVal.textContent = data.pitch !== undefined ? `${data.pitch}°` : '—°';
    irisVal.textContent  = data.iris  !== undefined ? data.iris.toFixed(3) : '—';

    if (data.alarm) {
        // Backend says: alarm condition detected
        consecutiveAlarms++;
        consecutiveSafe = 0;

        // Only trigger alarm after ALARM_THRESHOLD consecutive positive readings
        // This prevents false alarms from single bad frames
        if (consecutiveAlarms >= ALARM_THRESHOLD) {
            if (true) {
                playAlarm();
                totalAlarmCount++;
                alarmCount.textContent = totalAlarmCount;
                addLog(`⚠️ Alarm triggered! Pitch: ${data.pitch}°`, 'alarm-log');
            }
            setUIState('alarming');
        }
    } else {
        // Backend says: looks safe (looking at screen)
        consecutiveSafe++;
        consecutiveAlarms = 0;

        if (consecutiveSafe >= SAFE_THRESHOLD) {
            if (isAlarmPlaying()) {
                stopAlarm();
                addLog('✅ Back on track.', 'safe-log');
            }
            setUIState('safe');
        }
    }
}

// ── setUIState(): Update all visual elements at once ──────────────────────
function setUIState(state) {
    // Remove all state classes first, then add the right one
    statusBlock.className = `status-block ${state}`;
    alarmOverlay.className = `alarm-overlay ${state === 'alarming' ? 'active' : ''}`;
    statusPill.className = `status-pill ${state}`;

    if (state === 'alarming') {
        statusIcon.textContent = '📵';
        statusText.textContent = 'PUT THE PHONE DOWN!';
        statusPill.textContent = '🚨 ALARM';
        document.title = '🚨 PUT PHONE DOWN — Doom Scroll Stop';  // Tab title changes even in background!
    } else if (state === 'safe') {
        statusIcon.textContent = '✅';
        statusText.textContent = 'LOOKING GOOD!';
        statusPill.textContent = 'SAFE';
        document.title = 'Doom Scroll Stop';
    } else {
        statusIcon.textContent = '👁️';
        statusText.textContent = 'MONITORING...';
        statusPill.textContent = 'ACTIVE';
        document.title = 'Doom Scroll Stop';
    }
}

// ── addLog(): Add an entry to the event log ───────────────────────────────
function addLog(message, cssClass = '') {
    const li = document.createElement('li');        // Create a new <li> element
    li.className = `log-item ${cssClass}`;

    // Add timestamp prefix
    const now = new Date();
    const time = now.toTimeString().slice(0, 8);    // "HH:MM:SS"
    li.textContent = `[${time}] ${message}`;

    logList.prepend(li);    // Add to top of list (newest first)

    // Keep log from growing too long
    if (logList.children.length > 50) {
        logList.removeChild(logList.lastChild);     // Remove oldest entry
    }
}

// ── updateSessionTime(): Update the session timer display ─────────────────
function updateSessionTime() {
    if (!sessionStartTime) return;

    const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);    // Seconds
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');  // "MM"
    const seconds = (elapsed % 60).toString().padStart(2, '0');            // "SS"

    sessionTime.textContent = `${minutes}:${seconds}`;
}
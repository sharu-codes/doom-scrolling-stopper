// alarm.js — Controls the alarm sound

// Create an Audio object pointing to our alarm file.
// The browser loads alarm.wav from the same folder as index.html.
const alarmSound = new Audio('alarm.wav');

alarmSound.loop = false;     // Keep repeating the alarm until manually stopped

let alarmPlaying = false;   // Track if alarm is currently on

// ── playAlarm(): Start the alarm sound ────────────────────────────────────
function playAlarm() {
    if (alarmPlaying) return;   // Don't restart if already playing

    alarmPlaying = true;

    // .play() returns a Promise — we must handle it to avoid browser errors
    alarmSound.play().catch(err => {
        // Browsers block autoplay until user interacts with page first.
        // If this errors, it means no user interaction yet — ignore silently.
        console.log('Alarm play blocked by browser:', err);
    });
}

// ── stopAlarm(): Stop the alarm sound ────────────────────────────────────
function stopAlarm() {
    if (!alarmPlaying) return;  // Already stopped — nothing to do

    alarmPlaying = false;
    alarmSound.pause();         // Pause the audio
    alarmSound.currentTime = 0; // Rewind to the beginning for next time
}

// ── isAlarmPlaying(): Check current state ─────────────────────────────────
function isAlarmPlaying() {
    return alarmPlaying;
}
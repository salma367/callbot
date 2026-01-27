const callBtn = document.getElementById("callBtn");

let ws;
let mediaRecorder;
let audioChunks = [];
let isCallActive = false;
let isRecording = false;

/* ---------- Audio playback ---------- */
function playAIAudio(mp3Bytes) {
    const blob = new Blob([mp3Bytes], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audio.onended = () => {
        ws.send(JSON.stringify({ event: "ready_for_user" }));
        startRecording();
    };

    audio.play();
}

/* ---------- Recording ---------- */
async function startRecording() {
    if (isRecording) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    isRecording = true;

    mediaRecorder.ondataavailable = (e) => {
        audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunks, { type: "audio/webm" });
        ws.send(blob);
        isRecording = false;
    };

    mediaRecorder.start();

    // hard stop after 4 seconds (single turn)
    setTimeout(() => {
        if (mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        }
    }, 4000);
}

/* ---------- WebSocket ---------- */
function startCall() {
    ws = new WebSocket("ws://localhost:8000/ws/voice");
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
        callBtn.classList.add("active");
        callBtn.textContent = "IN CALL";
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            const msg = JSON.parse(event.data);
            if (msg.event === "ai_done") {
                // handled by audio.onended
            }
            return;
        }

        // binary MP3 from AI
        playAIAudio(event.data);
    };

    ws.onclose = () => {
        callBtn.classList.remove("active");
        callBtn.textContent = "START CALL";
        isCallActive = false;
    };
}

/* ---------- Button ---------- */
callBtn.onclick = () => {
    if (isCallActive) return;
    isCallActive = true;
    startCall();
};
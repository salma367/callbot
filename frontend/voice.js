const callBtn = document.getElementById("callBtn");
const statusText = document.getElementById("status");
const decisionText = document.getElementById("decision");
const confidenceText = document.getElementById("confidence");
const clarificationText = document.getElementById("clarifications");
const summaryContainer = document.getElementById("summary-container");
const summaryText = document.getElementById("summary-text");
const avatar = document.querySelector(".avatar");

const escalationScreen = document.getElementById("escalation-screen");
const agentInfo = document.getElementById("agent-info");
const callIdSpan = document.getElementById("call-id");
const generateReportBtn = document.getElementById("generate-report");
const reportOutput = document.getElementById("report-output");

let ws = null;
let mediaRecorder = null;
let audioChunks = [];
let isCallActive = false;
let isRecording = false;
let sessionId = null;
let clarificationCount = 0;
let stopAudio = false;
let stream = null;

// ---------- Audio playback ----------
function playAIAudio(mp3Bytes, callback = null) {
    if (stopAudio) return;

    const blob = new Blob([mp3Bytes], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    statusText.textContent = "AI speaking...";

    audio.onended = () => {
        URL.revokeObjectURL(url);
        if (stopAudio) return;
        statusText.textContent = "Listening...";
        if (callback) callback();
        else startRecording();
    };

    audio.play();
}

// ---------- Recording ----------
async function startRecording() {
    if (isRecording || !isCallActive || stopAudio) return;

    try {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        isRecording = true;

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            if (audioChunks.length > 0 && ws && isCallActive && !stopAudio) {
                const blob = new Blob(audioChunks, { type: "audio/webm" });
                ws.send(blob);
            }
            isRecording = false;
        };

        mediaRecorder.start();

        setTimeout(() => {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
            }
        }, 8000);

    } catch (error) {
        console.error("Error starting recording:", error);
        statusText.textContent = "Error accessing microphone";
    }
}

// ---------- Stop recording + call ----------
function endRecordingAndCall() {
    stopAudio = true;

    if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    isRecording = false;

    if (ws) {
        ws.close();
        ws = null;
    }
}

// ---------- Show escalation screen ----------
function showEscalationScreen(msg) {
    statusText.textContent = "Transferred to agent";
    escalationScreen.style.display = "block";
    agentInfo.textContent = `${msg.agent.agent_name} (${msg.agent.department})`;
    callIdSpan.textContent = sessionId;

    if (decisionText) decisionText.textContent = `Decision: ${msg.decision}`;
    callBtn.style.display = "none";
    summaryContainer.style.display = "none";
}

// ---------- Call end ----------
function endCall() {
    endRecordingAndCall();

    callBtn.classList.remove("active");
    avatar.classList.remove("active");
    callBtn.querySelector(".label").textContent = "Start Call";
    statusText.textContent = "Call ended";
    callBtn.style.display = "block";

    if (sessionId && !stopAudio) {
        fetch(`http://localhost:8000/call/end?call_id=${sessionId}`)
            .then(res => res.json())
            .then(data => {
                summaryContainer.style.display = "block";
                summaryText.textContent = data.summary || "No summary available";
            });
    }
}

// ---------- WebSocket ----------
function startCall() {
    stopAudio = false;
    sessionId = null;
    clarificationCount = 0;
    isCallActive = false;

    escalationScreen.style.display = "none";
    summaryContainer.style.display = "none";
    if (decisionText) decisionText.textContent = "";
    if (confidenceText) confidenceText.textContent = "";
    if (clarificationText) clarificationText.textContent = "";

    ws = new WebSocket("ws://localhost:8000/ws/voice");
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
        console.log("[DEBUG] WS connected");
        isCallActive = true;
        callBtn.classList.add("active");
        avatar.classList.add("active");
        callBtn.querySelector(".label").textContent = "End Call";
        statusText.textContent = "Connected, waiting for AI...";
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            const msg = JSON.parse(event.data);

            if (msg.call_id) sessionId = msg.call_id;

            // ---------- Escalation handling ----------
            if (msg.decision === "AGENT" && msg.agent) {
                stopAudio = true;

                // Play French escalation message first
                const ttsMessage = "Votre demande est trop complexe. Vous allez être transféré à un agent humain.";
                if (msg.audio_response) {
                    // If backend sent TTS, play it
                    playAIAudio(msg.audio_response, () => showEscalationScreen(msg));
                } else {
                    // Otherwise, use our local message (optional: send to backend TTS)
                    const utterance = new SpeechSynthesisUtterance(ttsMessage);
                    utterance.lang = "fr-FR";
                    utterance.onend = () => showEscalationScreen(msg);
                    speechSynthesis.speak(utterance);
                }
                endRecordingAndCall();
                return;
            }

            // ---------- Standard AI turn completion ----------
            if (msg.event === "ai_done") {
                if (msg.decision) decisionText.textContent = `Decision: ${msg.decision}`;
                if (msg.confidence !== undefined) confidenceText.textContent = `Confidence: ${msg.confidence}`;
                if (msg.clarification_count !== undefined) {
                    clarificationCount = msg.clarification_count;
                    clarificationText.textContent = `Clarifications: ${clarificationCount}`;
                }
                if (isCallActive && !stopAudio) setTimeout(startRecording, 500);
            }

            return;
        }

        // ---------- Binary audio ----------
        if (!stopAudio && isCallActive) playAIAudio(event.data);
    };

    ws.onclose = () => endCall();
    ws.onerror = (error) => { console.error(error); statusText.textContent = "Connection error"; endCall(); };
}

// ---------- Button ----------
callBtn.onclick = () => {
    if (!isCallActive) startCall();
    else endCall();
};

// ---------- Generate report ----------
generateReportBtn.onclick = () => {
    if (sessionId) {
        reportOutput.textContent = `Report for Call ID ${sessionId}:\n\n`;
        reportOutput.textContent += `Agent: ${agentInfo.textContent}\n`;
        reportOutput.textContent += `Decision: Escalated\n`;
        reportOutput.textContent += `Reason: Customer needs human assistance\n`;
        reportOutput.textContent += `Time: ${new Date().toLocaleString()}`;
    }
};

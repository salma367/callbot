// ---------- DOM Elements ----------
const userForm = document.getElementById("user-form");
const submitUserBtn = document.getElementById("submitUser");
const callContainer = document.getElementById("call-container");
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
let clientId = null;
let userName = null;
let userPhone = null;
let clarificationCount = 0;
let stopAudio = false;
let stream = null;

// ---------- Pre-call Registration ----------
submitUserBtn.onclick = async () => {
    userName = document.getElementById("fullName").value.trim();
    userPhone = document.getElementById("phoneNumber").value.trim();

    if (!userName || !userPhone) { alert("Veuillez remplir votre nom et numéro !"); return; }
    if (userName.length > 50) { alert("Votre nom est trop long (max 50 caractères)."); return; }

    const phoneRegex = /^\+212\s?\d{9}$/;
    if (!phoneRegex.test(userPhone)) { alert('Le numéro doit être au format "+212 123456789".'); return; }

    userPhone = userPhone.replace(/\s/g, "");

    try {
        const res = await fetch(`http://localhost:8000/call/start?user_name=${encodeURIComponent(userName)}&phone_number=${encodeURIComponent(userPhone)}`);
        const data = await res.json();
        if (data.error) { alert(data.error); return; }

        sessionId = data.call_id;
        clientId = data.client_id;

        console.log("Call started:", data);

        userForm.style.display = "none";
        callContainer.style.display = "block";
        statusText.textContent = "Cliquez sur Start Call pour commencer l'appel";
    } catch (err) {
        console.error("Error starting call:", err);
        alert("Impossible de contacter le serveur. Vérifiez qu'il est en cours d'exécution.");
    }
};

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
let isAISpeaking = false;

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
    isRecording = false;
}

async function startRecording() {
    if (isRecording || !isCallActive || stopAudio || !ws || ws.readyState !== WebSocket.OPEN || isAISpeaking) return;

    try {
        if (stream) stream.getTracks().forEach(track => track.stop());
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        isRecording = true;

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            if (audioChunks.length > 0 && ws && isCallActive && !stopAudio && !isAISpeaking) {
                const blob = new Blob(audioChunks, { type: "audio/webm" });
                ws.send(blob);
            }
            isRecording = false;
        };

        mediaRecorder.start();
        setTimeout(() => {
            if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
        }, 8000);

    } catch (error) {
        console.error("Error starting recording:", error);
        statusText.textContent = "Error accessing microphone";
    }
}

// ---------- End call ----------
function endCall({ keepEscalationUI = false } = {}) {
    if (!isCallActive) return;
    console.log("[DEBUG] Ending call");

    stopAudio = true;

    if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
    if (stream) { stream.getTracks().forEach(track => track.stop()); stream = null; }
    isRecording = false;

    if (ws && ws.readyState === WebSocket.OPEN) {
        try { ws.send(JSON.stringify({ event: "end_call" })); }
        catch (e) { console.warn("Failed to notify backend:", e); }
        try { ws.close(); } catch (e) { }
        ws = null;
    }

    isCallActive = false;
    callBtn.classList.remove("active");
    avatar.classList.remove("active");
    callBtn.querySelector(".label").textContent = "Start Call";
    statusText.textContent = "Call ended";

    decisionText.textContent = "";
    confidenceText.textContent = "";
    clarificationText.textContent = "";
    summaryContainer.style.display = "none";

    // Only hide escalation screen if not keeping it
    if (!keepEscalationUI) escalationScreen.style.display = "none";
}
// ---------- WebSocket ----------
function startCall() {
    if (!sessionId) { alert("Veuillez d'abord valider vos informations !"); return; }

    stopAudio = false;
    clarificationCount = 0;
    isCallActive = false;

    escalationScreen.style.display = "none";
    summaryContainer.style.display = "none";
    decisionText.textContent = "";
    confidenceText.textContent = "";
    clarificationText.textContent = "";

    ws = new WebSocket("ws://localhost:8000/ws/voice");
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
        console.log("[DEBUG] WS connected");
        isCallActive = true;
        callBtn.classList.add("active");
        avatar.classList.add("active");
        callBtn.querySelector(".label").textContent = "End Call";
        statusText.textContent = "Connected, waiting for AI...";

        ws.send(JSON.stringify({
            event: "register_client",
            client_id: clientId,
            user_name: userName,
            phone_number: userPhone
        }));
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            const msg = JSON.parse(event.data);

            // Keep sessionId updated
            if (msg.call_id) sessionId = msg.call_id;

            // ---------- Escalation handling ----------
            if (msg.decision === "AGENT" && msg.agent) {
                stopAudio = true; // Prevent further recording/playback

                const ttsMessage = "Votre demande nécessite l'intervention d'un agent humain. Vous allez être transféré maintenant.";

                if (msg.audio_stream) {
                    // Backend will stream binary audio; the binary handler will play it and call showEscalationScreen when finished.
                    // Do nothing here; wait for binary audio to arrive.
                } else if (msg.audio_response) {
                    // If backend included audio bytes directly in JSON (rare), play them
                    playAIAudio(msg.audio_response, () => showEscalationScreen(msg));
                } else {
                    // Otherwise, use browser SpeechSynthesis
                    const utterance = new SpeechSynthesisUtterance(ttsMessage);
                    utterance.lang = "fr-FR";
                    utterance.onend = () => showEscalationScreen(msg);
                    speechSynthesis.speak(utterance);
                }

                // End call but keep escalation UI visible
                endCall({ keepEscalationUI: true });
                return;
            }

            // ---------- Handle AI speaking ----------
            if (msg.event === "ai_speaking") {
                console.log("[DEBUG] AI is speaking, stopping recording");
                isAISpeaking = true;
                stopRecording();
                return;
            }

            // ---------- Handle AI turn done ----------
            if (msg.event === "ai_done") {
                isAISpeaking = false;
                if (msg.decision) decisionText.textContent = `Decision: ${msg.decision}`;
                if (msg.confidence !== undefined) confidenceText.textContent = `Confidence: ${msg.confidence}`;
                if (msg.clarification_count !== undefined) {
                    clarificationCount = msg.clarification_count;
                    clarificationText.textContent = `Clarifications: ${clarificationCount}`;
                }

                // ---------- Handle user goodbye ----------
                if (msg.reason && msg.reason === "USER_GOODBYE") {
                    statusText.textContent = "Call ended by user.";
                    summaryContainer.style.display = "block";
                    endCall();
                    return;
                }

                // ---------- Normal AI turn: start recording ----------
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

// ---------- Buttons ----------
callBtn.onclick = () => { if (!isCallActive) startCall(); else endCall(); };

generateReportBtn.onclick = () => {
    if (sessionId) {
        reportOutput.textContent = `Report for Call ID ${sessionId} (Client: ${userName}, Phone: ${userPhone}, ID: ${clientId}):\n\n`;
        reportOutput.textContent += `Agent: ${agentInfo.textContent}\n`;
        reportOutput.textContent += `Decision: Escalated\n`;
        reportOutput.textContent += `Reason: Customer needs human assistance\n`;
        reportOutput.textContent += `Time: ${new Date().toLocaleString()}`;
    }
};
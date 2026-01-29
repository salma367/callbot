// Helper function for displaying escalation screen
// Add this to your voice.js file or include it separately

function showEscalationScreen(msg) {
    console.log("[DEBUG] Showing escalation screen", msg);

    const escalationScreen = document.getElementById("escalation-screen");
    const agentInfo = document.getElementById("agent-info");
    const callIdSpan = document.getElementById("call-id");

    // Display agent information (always Sara)
    agentInfo.textContent = "Agent: Sara";

    // Display call ID
    callIdSpan.textContent = sessionId || "N/A";

    // Show the escalation screen with animation
    escalationScreen.style.display = "block";
    escalationScreen.classList.add("fade-in");

    // Update status
    statusText.textContent = "Transfert vers un agent humain...";

    // Optional: Show summary if available
    if (msg.summary) {
        summaryContainer.style.display = "block";
        summaryText.textContent = msg.summary;
    }
}

// Enhanced report generation with simple formatting
function enhanceReportGeneration() {
    const generateReportBtn = document.getElementById("generate-report");
    const reportOutput = document.getElementById("report-output");

    generateReportBtn.onclick = () => {
        if (!sessionId) {
            alert("Aucun appel actif");
            return;
        }

        const timestamp = new Date().toLocaleString('fr-FR');

        reportOutput.textContent = `RAPPORT D'APPEL

Call ID: ${sessionId}
Client: ${userName}
Phone: ${userPhone}
Agent: Sara
Status: Escaladé
Time: ${timestamp}
`;

        // Show the output
        reportOutput.style.display = "block";
        reportOutput.classList.add("fade-in");
    };
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceReportGeneration);
} else {
    enhanceReportGeneration();
}

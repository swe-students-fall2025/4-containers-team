let pollInterval = null;

async function loadLatestAnalysis() {
    try {
        // Load updated counts
        loadTotalUploads();

        // Get the user's upload_id from localStorage
        const uploadId = localStorage.getItem("userUploadId");

        if (!uploadId) {
            // User hasn't uploaded anything in this session - show N/A
            const languageEl = document.getElementById("latest-language");
            const transcriptEl = document.getElementById("latest-transcript");
            languageEl.textContent = "Language detected: N/A";
            transcriptEl.textContent = "Transcript: N/A";
            stopPolling();
            return;
        }

        // Fetch analysis for this specific upload
        const res = await fetch(`/api/latest-analysis?upload_id=${uploadId}`);
        const data = await res.json();

        if (data.error) {
            console.error("Error loading analysis:", data.error);
            return;
        }

        const languageEl = document.getElementById("latest-language");
        const transcriptEl = document.getElementById("latest-transcript");

        if (!data.has_upload) {
            // Upload not found (maybe deleted) - clear localStorage and show N/A
            localStorage.removeItem("userUploadId");
            languageEl.textContent = "Language detected: N/A";
            transcriptEl.textContent = "Transcript: N/A";
            stopPolling();
            return;
        }

        if (data.status === "processing") {
            // Upload exists but analysis not ready - show processing
            languageEl.textContent = "Language detected: Processing…";
            transcriptEl.textContent = "Transcript: Processing…";
            // Start polling if not already polling
            if (!pollInterval) {
                startPolling();
            }
            return;
        }

        if (data.status === "completed" && data.analysis) {
            // Analysis is ready - show results
            languageEl.textContent = "Language detected: " + data.analysis.language;
            transcriptEl.textContent = "Transcript: " + (data.analysis.transcript || "None");
            // Stop polling once we have the result
            stopPolling();
            return;
        }
    } catch (err) {
        console.error("Failed to load latest analysis:", err);
    }
}

function startPolling() {
    // Poll every 2 seconds while processing
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    pollInterval = setInterval(() => {
        loadLatestAnalysis();
    }, 2000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// // Load on page load - will show N/A if no upload_id in localStorage
// document.addEventListener("DOMContentLoaded", () => {
//     loadLatestAnalysis();
//     loadTotalUploads();
// });

// When upload completes, start polling for results
document.addEventListener("uploadComplete", (event) => {
    // Immediately check and start polling
    loadLatestAnalysis();
    // Start polling to check for analysis completion
    startPolling();
});

// Clean up polling when page unloads
window.addEventListener("beforeunload", () => {
    stopPolling();
});

async function loadTotalUploads() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        document.getElementById("total-uploads").textContent =
            data.total_uploads ?? 0;
    } catch (err) {
        console.error("Failed to load total uploads:", err);
    }
}

// Load on page load - will show N/A if no upload_id in localStorage
document.addEventListener("DOMContentLoaded", () => {
    loadLatestAnalysis();
    loadTotalUploads();
});
async function loadMLResults() {
    try {
        const res = await fetch("/api/ml-results?limit=1");
        const data = await res.json();

        if (!data.results || data.results.length === 0) {
            document.getElementById("latest-language").textContent = "Language detected: N/A";
            document.getElementById("latest-transcript").textContent = "Transcript: N/A";
            return;
        }

        const latest = data.results[0];

        document.getElementById("latest-language").textContent =
            "Language detected: " + latest.language;

        document.getElementById("latest-transcript").textContent =
            "Transcript: " + (latest.transcript || "None");

    } catch (err) {
        console.error("Failed to load ML results:", err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadMLResults();
});

document.addEventListener("uploadComplete", () => {
    document.getElementById("latest-language").textContent =
        "Language detected: Processing…";

    document.getElementById("latest-transcript").textContent =
        "Transcript: Processing…";
    loadMLResults();
    
});

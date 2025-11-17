document.getElementById("recordBtn").onclick = async () => {
    const status = document.getElementById("status");
    const countdown = document.getElementById("countdown");

    status.textContent = "initializing microphone...";

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    let chunks = [];

    mediaRecorder.ondataavailable = e => chunks.push(e.data);

    mediaRecorder.onstop = async () => {
        countdown.textContent = "done!";
        status.textContent = "uploading audio...";

        if (chunks.length === 0) {
            status.textContent = "Error: No audio data recorded";
            return;
        }

        const blob = new Blob(chunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                status.textContent = "recording uploaded:)";
                // Dispatch event to notify dashboard to refresh
                document.dispatchEvent(new CustomEvent('uploadComplete'));
            } else {
                status.textContent = `Upload failed: ${data.error || 'Unknown error'}`;
            }
        } catch (error) {
            status.textContent = `Upload failed: ${error.message}`;
        }
    };

    mediaRecorder.start();
    status.textContent = "recording...";

    // countdown timer
    let timeLeft = 10;
    countdown.textContent = `time left: ${timeLeft}s`;

    const interval = setInterval(() => {
        timeLeft--;
        countdown.textContent = `time left: ${timeLeft}s`;

        if (timeLeft <= 0) {
            clearInterval(interval);
        }
    }, 1000);

    // stop after 10 seconds
    setTimeout(() => {
        if (mediaRecorder.state !== 'inactive') {
            mediaRecorder.requestData(); // Request any remaining data
            mediaRecorder.stop();
        }
        status.textContent = "processing...";
    }, 10000);
};

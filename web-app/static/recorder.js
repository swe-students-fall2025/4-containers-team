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

        const blob = new Blob(chunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append("audio", blob, "recording.webm");

        await fetch("/upload", {
            method: "POST",
            body: formData
        });

        status.textContent = "recording uploaded:)";
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
        mediaRecorder.stop();
        status.textContent = "processing...";
    }, 10000);
};

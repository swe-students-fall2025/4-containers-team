(() => {
    const recordBtn = document.getElementById('recordBtn');
    const status = document.getElementById('status');
    const countdown = document.getElementById('countdown');

    let mediaRecorder = null;
    let chunks = [];
    let recording = false;
    let intervalId = null;
    let timeoutId = null;
    let timeLeft = 10;

    function resetUI() {
        recording = false;
        recordBtn.textContent = 'Start Recording';
        recordBtn.classList.remove('recording');
        recordBtn.disabled = false;
        countdown.textContent = '';
        status.textContent = '';
    }

    async function startRecording() {
        try {
            recordBtn.disabled = true; // prevent double-click during init
            status.textContent = 'initializing microphone...';
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            chunks = [];

            mediaRecorder.ondataavailable = (e) => chunks.push(e.data);

            mediaRecorder.onstop = async () => {
                // stop the countdown/timeout if still running
                if (intervalId) clearInterval(intervalId);
                if (timeoutId) clearTimeout(timeoutId);

                countdown.textContent = 'done!';
                status.textContent = 'uploading audio...';

                if (chunks.length === 0) {
                    status.textContent = 'Error: No audio data recorded';
                    resetUI();
                    return;
                }

                const blob = new Blob(chunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', blob, 'recording.webm');

                try {
                    // disable button while uploading
                    recordBtn.disabled = true;
                    const response = await fetch('/upload', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (response.ok) {
                        status.textContent = 'recording uploaded :)';
                        document.dispatchEvent(new CustomEvent('uploadComplete'));
                    } else {
                        status.textContent = `Upload failed: ${data.error || 'Unknown error'}`;
                    }
                } catch (err) {
                    status.textContent = `Upload failed: ${err.message}`;
                } finally {
                    // restore UI after upload
                    resetUI();
                }
            };

            mediaRecorder.start();
            recording = true;
            recordBtn.classList.add('recording');
            recordBtn.textContent = 'End Recording';
            recordBtn.disabled = false; // allow clicking to end early
            status.textContent = 'recording...';

            // countdown
            timeLeft = 10;
            countdown.textContent = `time left: ${timeLeft}s`;
            intervalId = setInterval(() => {
                timeLeft -= 1;
                countdown.textContent = `time left: ${timeLeft}s`;
                if (timeLeft <= 0) {
                    clearInterval(intervalId);
                }
            }, 1000);

            // automatic stop after 10s
            timeoutId = setTimeout(() => {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.requestData();
                    mediaRecorder.stop();
                }
                status.textContent = 'processing...';
            }, 10000);
        } catch (err) {
            status.textContent = `Microphone error: ${err.message}`;
            resetUI();
        }
    }

    function stopRecordingEarly() {
        if (!mediaRecorder) return;
        if (intervalId) clearInterval(intervalId);
        if (timeoutId) clearTimeout(timeoutId);
        if (mediaRecorder.state !== 'inactive') {
            mediaRecorder.requestData();
            mediaRecorder.stop();
        }
        status.textContent = 'stopped';
    }

    recordBtn.addEventListener('click', (e) => {
        if (!recording) {
            startRecording();
        } else {
            // currently recording -> end early
            stopRecordingEarly();
        }
    });

    // initialize UI
    resetUI();
})();

let mediaRecorder;
let audioChunks = [];

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
            mediaRecorder.onstop = () => {
                let audioBlob = new Blob(audioChunks, { type: "audio/wav" });
                let audioUrl = URL.createObjectURL(audioBlob);
                document.getElementById("audioPlayer").src = audioUrl;
                
                let formData = new FormData();
                formData.append("audio", audioBlob, "recorded_audio.wav");

                fetch("/upload", { method: "POST", body: formData })
                .then(response => response.json())
                .then(data => updateFeatures(data.features))
                .catch(error => console.error("Error:", error));
            };
            mediaRecorder.start();
            audioChunks = [];
        })
        .catch(error => console.error("Error accessing microphone:", error));
}

function stopRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
    }
}

function uploadAudio() {
    let fileInput = document.getElementById("audioFile");
    if (fileInput.files.length === 0) {
        alert("Please select an audio file first!");
        return;
    }

    let formData = new FormData();
    formData.append("audio", fileInput.files[0]);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => updateFeatures(data.features))
    .catch(error => console.error("Error:", error));
}

function updateFeatures(features) {
    if (features) {
        document.getElementById("jitter").innerText = features.jitter.toFixed(6);
        document.getElementById("shimmer").innerText = features.shimmer.toFixed(6);
        document.getElementById("hnr").innerText = features.hnr.toFixed(6);
        document.getElementById("ppe").innerText = features.ppe.toFixed(6);
    } else {
        alert("Error extracting features!");
    }
}

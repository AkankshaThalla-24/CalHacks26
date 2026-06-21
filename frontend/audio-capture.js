// Captures the page's actual tab audio (including the embedded YouTube
// video) via getDisplayMedia tab-capture, downsamples it to 16kHz mono
// PCM, and streams it to pipeline_server's /audio-in over WebSocket.
// This is what lets stt_service.py --from-browser transcribe whatever
// video is currently loaded on this page, with no separate download step.
//
// Browser constraint, not a bug: capturing tab audio requires an explicit
// user click and a one-time "Share this tab + include audio" permission
// dialog — there's no way around that, it's a security boundary.

const AUDIO_WS = window.AUDIO_WS || "ws://localhost:8000/audio-in";
const TARGET_SAMPLE_RATE = 16000;

let captureStream = null;
let audioContext = null;
let processorNode = null;
let audioSocket = null;
let capturing = false;

function downsampleTo16kMono(input, inputSampleRate) {
  if (inputSampleRate === TARGET_SAMPLE_RATE) return input;
  const ratio = inputSampleRate / TARGET_SAMPLE_RATE;
  const newLength = Math.round(input.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetInput = 0;
  while (offsetResult < newLength) {
    const nextOffsetInput = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;
    for (let i = offsetInput; i < nextOffsetInput && i < input.length; i++) {
      accum += input[i];
      count++;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult++;
    offsetInput = nextOffsetInput;
  }
  return result;
}

function floatTo16BitPCM(float32) {
  const out = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function updateCaptureUI(status) {
  const btn = document.getElementById("capture-btn");
  if (!btn) return;
  if (status) {
    btn.textContent = status;
  } else {
    btn.textContent = capturing ? "Stop audio capture" : "Start audio capture";
  }
  btn.classList.toggle("capturing", capturing);
}

function connectAudioSocket() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(AUDIO_WS);
    ws.binaryType = "arraybuffer";
    const timeout = setTimeout(() => {
      ws.close();
      reject(new Error("Timed out connecting to the backend. Is stt_service.py --from-browser running?"));
    }, 5000);
    ws.onopen = () => {
      clearTimeout(timeout);
      resolve(ws);
    };
    ws.onerror = () => {
      clearTimeout(timeout);
      reject(new Error("Couldn't reach ws://localhost:8000/audio-in. Is stt_service.py --from-browser running?"));
    };
  });
}

async function startCapture() {
  if (capturing) return;
  updateCaptureUI("Connecting…");

  // Unmute the embedded player — captured tab audio is silent otherwise,
  // since autoplay requires starting muted.
  if (window.ytPlayer && window.ytPlayer.unMute) {
    window.ytPlayer.unMute();
    window.ytPlayer.setVolume(100);
  }

  // Connect to the backend FIRST — fail loudly here rather than silently
  // capturing audio nobody is listening for.
  try {
    audioSocket = await connectAudioSocket();
  } catch (err) {
    updateCaptureUI();
    alert(err.message);
    return;
  }
  audioSocket.onclose = () => {
    if (capturing) {
      console.warn("audio-in WebSocket closed unexpectedly");
      stopCapture();
    }
  };

  captureStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
  const audioTracks = captureStream.getAudioTracks();
  if (audioTracks.length === 0) {
    alert('No audio track captured — when prompted, make sure to check "Share tab audio".');
    captureStream.getTracks().forEach((t) => t.stop());
    captureStream = null;
    audioSocket.close();
    audioSocket = null;
    updateCaptureUI();
    return;
  }
  captureStream.getVideoTracks().forEach((t) => t.stop()); // only need audio

  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(new MediaStream(audioTracks));
  processorNode = audioContext.createScriptProcessor(4096, 1, 1);

  processorNode.onaudioprocess = (e) => {
    if (!audioSocket || audioSocket.readyState !== WebSocket.OPEN) return;
    const input = e.inputBuffer.getChannelData(0);
    const downsampled = downsampleTo16kMono(input, audioContext.sampleRate);
    const pcm16 = floatTo16BitPCM(downsampled);
    audioSocket.send(pcm16.buffer);
  };

  // ScriptProcessorNode only fires while connected to a destination; route
  // through a silent gain node so we don't double-play the tab's own audio.
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;
  source.connect(processorNode);
  processorNode.connect(silentGain);
  silentGain.connect(audioContext.destination);

  audioTracks[0].addEventListener("ended", stopCapture); // user clicked "Stop sharing"

  capturing = true;
  updateCaptureUI();
}

function stopCapture() {
  if (!capturing) return;
  capturing = false;
  if (processorNode) processorNode.disconnect();
  if (audioContext) audioContext.close();
  if (captureStream) captureStream.getTracks().forEach((t) => t.stop());
  if (audioSocket) audioSocket.close();
  processorNode = audioContext = captureStream = audioSocket = null;
  updateCaptureUI();
}

document.getElementById("capture-btn").addEventListener("click", () => {
  if (capturing) {
    stopCapture();
  } else {
    startCapture().catch((err) => {
      console.error(err);
      alert("Couldn't start tab audio capture: " + err.message);
    });
  }
});

// YouTube IFrame embed. Pick any video via ?v=<url-or-id> in the page URL,
// the video-picker input box, or window.YT_VIDEO_ID. Falls back to a
// default id if none of those are set.

const DEFAULT_VIDEO_ID = "OJlwIdoFz9A"; // may be stale if that stream ended

function extractVideoId(input) {
  if (!input) return null;
  input = input.trim();
  if (/^[\w-]{11}$/.test(input)) return input; // already a bare video id
  try {
    const url = new URL(input);
    if (url.hostname.includes("youtu.be")) return url.pathname.slice(1);
    if (url.searchParams.get("v")) return url.searchParams.get("v");
    const m = url.pathname.match(/\/(live|embed|shorts)\/([\w-]{11})/);
    if (m) return m[2];
  } catch (e) {
    // not a parseable URL
  }
  return null;
}

const pageParams = new URLSearchParams(location.search);
let VIDEO_ID = extractVideoId(pageParams.get("v")) || window.YT_VIDEO_ID || DEFAULT_VIDEO_ID;

let ytPlayer = null;

// Called automatically by the IFrame API script.
function onYouTubeIframeAPIReady() {
  ytPlayer = new YT.Player("player", {
    videoId: VIDEO_ID,
    playerVars: {
      autoplay: 1,
      mute: 1, // browsers require mute for autoplay
      controls: 1,
      rel: 0,
      modestbranding: 1,
    },
  });
  window.ytPlayer = ytPlayer; // exposed so audio-capture.js can unmute it
}

window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady;

// Public: load any YouTube URL or bare video ID at runtime.
window.loadYouTubeVideo = function (input) {
  const id = extractVideoId(input);
  if (!id) {
    alert("Couldn't find a YouTube video ID in that input.");
    return;
  }
  VIDEO_ID = id;
  if (ytPlayer && ytPlayer.loadVideoById) {
    ytPlayer.loadVideoById(id);
  }
};

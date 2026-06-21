// YouTube IFrame embed. Change VIDEO_ID to any live (or normal) YouTube video.
// Tip: a live World Cup / sports stream id makes the best demo.
const VIDEO_ID = window.YT_VIDEO_ID || "OJlwIdoFz9A"; // demo live stream reference

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
}

window.onYouTubeIframeAPIReady = onYouTubeIframeAPIReady;

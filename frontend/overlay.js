// Overlay behaviour: corner placement, drag, resize, language switch,
// and playing incoming sign-language clips with captions.

const overlay = document.getElementById("overlay");
const video = document.getElementById("sl-video");
const caption = document.getElementById("caption");
const gloss = document.getElementById("gloss");
const slBadge = document.getElementById("sl-badge");
const slSelect = document.getElementById("sl-select");
const conn = document.getElementById("conn");
const header = document.getElementById("overlay-header");
const resizeHandle = document.getElementById("resize-handle");

// ---- Corner placement ----
const cornerClasses = ["corner-tl", "corner-tr", "corner-bl", "corner-br"];
function setCorner(corner) {
  cornerClasses.forEach((c) => overlay.classList.remove(c));
  overlay.classList.add(`corner-${corner}`);
  // clear any drag offsets so the corner anchor takes effect
  overlay.style.top = overlay.style.left = overlay.style.right = overlay.style.bottom = "";
  const map = { tl: ["20px","20px","",""], tr: ["20px","","","20px"],
                bl: ["","20px","80px",""], br: ["","","80px","20px"] };
  const [top, left, bottom, right] = map[corner];
  overlay.style.top = top; overlay.style.left = left;
  overlay.style.bottom = bottom; overlay.style.right = right;
}
document.querySelectorAll("#corner-picker button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#corner-picker button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    setCorner(btn.dataset.corner);
  });
});

// ---- Drag (via header) ----
let dragging = false, dragDX = 0, dragDY = 0;
header.addEventListener("mousedown", (e) => {
  if (e.target === slSelect) return;
  dragging = true;
  const r = overlay.getBoundingClientRect();
  dragDX = e.clientX - r.left;
  dragDY = e.clientY - r.top;
  // switch to absolute positioning from the current spot
  overlay.style.right = overlay.style.bottom = "";
  overlay.style.left = r.left + "px";
  overlay.style.top = r.top + "px";
});
window.addEventListener("mousemove", (e) => {
  if (!dragging) return;
  overlay.style.left = (e.clientX - dragDX) + "px";
  overlay.style.top = (e.clientY - dragDY) + "px";
});
window.addEventListener("mouseup", () => (dragging = false));

// ---- Resize (drag the corner handle) ----
let resizing = false, startW = 0, startH = 0, startX = 0, startY = 0;
resizeHandle.addEventListener("mousedown", (e) => {
  e.stopPropagation();
  resizing = true;
  const r = overlay.getBoundingClientRect();
  startW = r.width; startH = r.height; startX = e.clientX; startY = e.clientY;
});
window.addEventListener("mousemove", (e) => {
  if (!resizing) return;
  overlay.style.width = Math.max(160, startW + (e.clientX - startX)) + "px";
  overlay.style.height = Math.max(120, startH + (e.clientY - startY)) + "px";
});
window.addEventListener("mouseup", () => (resizing = false));

// ---- Sign language switch ----
slSelect.addEventListener("change", () => {
  const lang = slSelect.value;
  slBadge.textContent = lang;
  window.streamClient.setLang(lang);
});

// ---- Clip playback queue ----
const queue = [];
let playing = false;

function enqueue(data) {
  queue.push(data);
  if (!playing) playNext();
}

function playNext() {
  if (queue.length === 0) { playing = false; return; }
  playing = true;
  const data = queue.shift();
  caption.textContent = data.caption || "";
  gloss.textContent = data.gloss || "";
  if (data.clipUrl) {
    video.src = data.clipUrl;
    video.play().catch(() => {});
    video.onended = () => playNext();
    // safety timeout in case a clip never fires 'ended'
    clearTimeout(video._t);
    video._t = setTimeout(playNext, 12000);
  } else {
    setTimeout(playNext, 1500);
  }
}

// ---- Wire up the stream ----
window.streamClient.onClip(enqueue);
window.streamClient.connect((status) => {
  conn.textContent = status === "live" ? "live" : "offline";
  conn.classList.toggle("live", status === "live");
});

// Consumes sign-language clip events from the pipeline over WebSocket.
// Event shape (mock + real pipeline both emit this):
//   { clipUrl, gloss, caption, ts, lang }
//
// Falls back gracefully if the socket is unavailable so the UI still loads.

const WS_URL = window.PIPELINE_WS || "ws://localhost:8000/ws";

class StreamClient {
  constructor() {
    this.handlers = [];
    this.lang = "ASL";
    this.ws = null;
  }

  onClip(fn) { this.handlers.push(fn); }

  setLang(lang) {
    this.lang = lang;
    // Tell the server which sign language we want (server may filter).
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "set_lang", lang }));
    }
  }

  connect(onStatus) {
    try {
      this.ws = new WebSocket(WS_URL);
    } catch (e) {
      onStatus && onStatus("offline");
      return;
    }
    this.ws.onopen = () => {
      onStatus && onStatus("live");
      this.ws.send(JSON.stringify({ type: "set_lang", lang: this.lang }));
    };
    this.ws.onclose = () => onStatus && onStatus("offline");
    this.ws.onerror = () => onStatus && onStatus("offline");
    this.ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      if (data.lang && data.lang !== this.lang) return; // ignore other languages
      this.handlers.forEach((h) => h(data));
    };
  }
}

window.streamClient = new StreamClient();

// Consumes sign-language clip events from pipeline_server.py over WebSocket.
// Event shape:
//   { clipUrl, gloss, caption, ts, lang }
//
// Falls back gracefully if the socket is unavailable so the UI still loads,
// and keeps retrying with backoff if the backend isn't up yet or drops.

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
    this._onStatus = onStatus;
    this._reconnectDelay = 1000;
    this._connectOnce();
  }

  _connectOnce() {
    try {
      this.ws = new WebSocket(WS_URL);
    } catch (e) {
      this._onStatus && this._onStatus("offline");
      this._scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this._onStatus && this._onStatus("live");
      this._reconnectDelay = 1000; // reset backoff on success
      this.ws.send(JSON.stringify({ type: "set_lang", lang: this.lang }));
    };
    this.ws.onclose = () => {
      this._onStatus && this._onStatus("offline");
      this._scheduleReconnect();
    };
    this.ws.onerror = () => this._onStatus && this._onStatus("offline");
    this.ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }
      if (data.lang && data.lang !== this.lang) return; // ignore other languages
      this.handlers.forEach((h) => h(data));
    };
  }

  _scheduleReconnect() {
    // The backend (stt_service.py) is often not running yet, or restarts
    // between runs — keep retrying with capped backoff instead of giving
    // up after the first failed/dropped connection.
    clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => {
      this._connectOnce();
      this._reconnectDelay = Math.min(10000, this._reconnectDelay * 1.5);
    }, this._reconnectDelay);
  }
}

window.streamClient = new StreamClient();

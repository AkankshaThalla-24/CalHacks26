"""Mock pipeline: stands in for Deepgram -> Claude -> Midjourney -> Redis.

Emits sign-language clip events over WebSocket on a timer so the frontend overlay
is fully demoable without the real backend. Swap the frontend's PIPELINE_WS to the
real endpoint when the team's pipeline is ready — the event shape is identical:

    { "clipUrl": str, "gloss": str, "caption": str, "ts": float, "lang": str }

Run:
    pip install -r requirements.txt
    uvicorn server:app --port 8000
"""

import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# A public sample MP4 stands in for generated sign-language clips.
# Replace with real ASL/BSL/... clip URLs (or Redis-served generated media).
SAMPLE_CLIP = "https://www.w3schools.com/html/mov_bbb.mp4"

# Scripted "live commentary" feed. caption = English shown to viewer;
# gloss = the target-language gloss the avatar would sign.
FEED = [
    {"caption": "Argentina break forward down the right wing.",
     "gloss": {"ASL": "ARGENTINA RIGHT-SIDE FORWARD GO",
               "BSL": "ARGENTINA RIGHT FORWARD RUN",
               "LSF": "ARGENTINE COTE-DROIT AVANCER",
               "CSL": "ARGENTINA RIGHT FORWARD",
               "JSL": "ARGENTINA MIGI MAE SUSUMU"}},
    {"caption": "GOAL! Messi makes it 1-0 in the 67th minute!",
     "gloss": {"ASL": "TIME 67 MESSI SCORE GOAL NOW 1-0",
               "BSL": "67-MINUTE MESSI GOAL SCORE 1-0",
               "LSF": "67-MINUTE MESSI BUT MARQUER 1-0",
               "CSL": "67 MINUTE MESSI GOAL 1-0",
               "JSL": "67-FUN MESSI GOORU 1-0"}},
    {"caption": "France appeal for offside, but the flag stays down.",
     "gloss": {"ASL": "FRANCE THINK OFFSIDE FLAG NO",
               "BSL": "FRANCE OFFSIDE CLAIM FLAG DOWN",
               "LSF": "FRANCE HORS-JEU DEMANDER DRAPEAU NON",
               "CSL": "FRANCE OFFSIDE FLAG NO",
               "JSL": "FRANCE OFFSIDE HATA NAI"}},
    {"caption": "Yellow card shown for a late challenge.",
     "gloss": {"ASL": "LATE TACKLE CARD YELLOW SHOW",
               "BSL": "LATE TACKLE YELLOW CARD",
               "LSF": "TACLE RETARD CARTON JAUNE",
               "CSL": "LATE FOUL YELLOW CARD",
               "JSL": "OSOI TACKLE KIIRO CARD"}},
    {"caption": "Substitution for France: fresh legs up front.",
     "gloss": {"ASL": "FRANCE CHANGE PLAYER NEW FRONT",
               "BSL": "FRANCE SUB NEW STRIKER ON",
               "LSF": "FRANCE CHANGEMENT JOUEUR NOUVEAU",
               "CSL": "FRANCE CHANGE PLAYER NEW",
               "JSL": "FRANCE KOOTAI ATARASHII MAE"}},
    {"caption": "Full time! Argentina win it 1-0.",
     "gloss": {"ASL": "FINISH ARGENTINA WIN 1-0",
               "BSL": "FULL-TIME ARGENTINA WIN 1-0",
               "LSF": "FIN ARGENTINE GAGNER 1-0",
               "CSL": "END ARGENTINA WIN 1-0",
               "JSL": "SHUURYOU ARGENTINA KACHI 1-0"}},
]

INTERVAL_SECONDS = 6


@app.get("/")
def health():
    return {"status": "ok", "feed_items": len(FEED)}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    lang = "ASL"
    idx = 0
    try:
        while True:
            # Non-blocking check for a language-change message from the client.
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.01)
                if msg.get("type") == "set_lang":
                    lang = msg.get("lang", lang)
            except asyncio.TimeoutError:
                pass  # no client message this tick — keep streaming

            item = FEED[idx % len(FEED)]
            await websocket.send_json(
                {
                    "clipUrl": SAMPLE_CLIP,
                    "gloss": item["gloss"].get(lang, ""),
                    "caption": item["caption"],
                    "ts": time.time(),
                    "lang": lang,
                }
            )
            idx += 1
            await asyncio.sleep(INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return

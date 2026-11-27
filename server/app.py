import asyncio
import json
import math
import os
import time
import uuid
from websockets.asyncio.server import serve

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8765"))
UPDATE_INTERVAL = 1.5

SCALES = {
    "C": [60, 62, 64, 65, 67, 69, 71],
    "D": [62, 64, 66, 67, 69, 71, 73],
    "E": [64, 66, 68, 69, 71, 73, 75],
    "F": [65, 67, 69, 70, 72, 74, 76],
    "G": [67, 69, 71, 72, 74, 76, 78],
    "A": [69, 71, 73, 74, 76, 78, 80],
}

CHORDS = {
    "C": [0, 2, 4],
    "Dm": [1, 3, 5],
    "Em": [2, 4, 6],
    "F": [3, 5, 0],
    "G": [4, 6, 1],
    "Am": [5, 0, 2],
}

SESSIONS = {}

def clamp(value, low, high):
    return max(low, min(high, value))

def safe_number(value, default, low, high):
    try:
        return clamp(float(value), low, high)
    except (TypeError, ValueError):
        return default

def infer_style(message):
    style = str(message.get("style", "Gospel")).strip()
    allowed = {
        "Gospel", "Worship", "Afrobeat",
        "Jazz", "Pop", "Reggae", "Soul"
    }
    return style if style in allowed else "Gospel"

def infer_key(message):
    key = str(message.get("key", "C")).strip()
    return key if key in SCALES else "C"

def infer_chord(message):
    chord = str(message.get("chord", "C")).strip()
    return chord if chord in CHORDS else "C"

def make_events(key, chord, style, bpm):
    scale = SCALES[key]
    chord_degrees = CHORDS[chord]
    beat_ms = 60000.0 / bpm

    # Each event is a MIDI note instruction.
    # The Android app must schedule these locally.
    events = []

    # Bass: root note on each beat.
    root = scale[chord_degrees[0]] - 24
    for beat in range(4):
        events.append({
            "time_ms": round(beat * beat_ms),
            "duration_ms": round(beat_ms * 0.75),
            "note": root,
            "velocity": 92,
            "instrument": "bass"
        })

    # Chord accompaniment.
    chord_notes = [
        scale[degree] + 12 for degree in chord_degrees
    ]

    for beat in range(4):
        if style in ("Worship", "Jazz", "Soul"):
            beat_position = beat * beat_ms
        elif style == "Reggae":
            beat_position = (beat + 0.5) * beat_ms
        else:
            beat_position = beat * beat_ms

        for note in chord_notes:
            events.append({
                "time_ms": round(beat_position),
                "duration_ms": round(beat_ms * 0.8),
                "note": note,
                "velocity": 65,
                "instrument": "keys"
            })

    # Simple melodic response.
    melody_degrees = chord_degrees + [chord_degrees[1]]
    for index, degree in enumerate(melody_degrees):
        events.append({
            "time_ms": round(index * beat_ms),
            "duration_ms": round(beat_ms * 0.45),
            "note": scale[degree] + 24,
            "velocity": 72,
            "instrument": "lead"
        })

    events.sort(key=lambda item: item["time_ms"])
    return events

def make_arrangement(message):
    key = infer_key(message)
    chord = infer_chord(message)
    style = infer_style(message)
    bpm = safe_number(message.get("bpm"), 90, 50, 180)

    return {
        "type": "arrangement",
        "protocol": "afrinode-live-band-v1",
        "session_id": message.get("session_id"),
        "timestamp_ms": int(time.time() * 1000),
        "key": key,
        "chord": chord,
        "style": style,
        "bpm": round(bpm, 1),
        "beats_per_bar": 4,
        "bar_duration_ms": round(240000 / bpm),
        "events": make_events(key, chord, style, bpm)
    }

async def send_json(websocket, payload):
    await websocket.send(json.dumps(payload))

async def handle_client(websocket):
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "last_sent": 0.0,
        "active": False
    }

    print("Connected:", session_id)

    try:
        await send_json(websocket, {
            "type": "connected",
            "protocol": "afrinode-live-band-v1",
            "session_id": session_id
        })

        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await send_json(websocket, {
                    "type": "error",
                    "message": "Message must be valid JSON"
                })
                continue

            if not isinstance(message, dict):
                await send_json(websocket, {
                    "type": "error",
                    "message": "Expected a JSON object"
                })
                continue

            message_type = message.get("type")

            if message_type == "ping":
                await send_json(websocket, {
                    "type": "pong",
                    "timestamp_ms": int(time.time() * 1000)
                })
                continue

            if message_type == "stop":
                SESSIONS[session_id]["active"] = False
                await send_json(websocket, {
                    "type": "stopped",
                    "session_id": session_id
                })
                continue

            if message_type == "start":
                SESSIONS[session_id]["active"] = True
                message["session_id"] = session_id
                await send_json(websocket, {
                    "type": "started",
                    "session_id": session_id
                })
                arrangement = make_arrangement(message)
                await send_json(websocket, arrangement)
                SESSIONS[session_id]["last_sent"] = time.monotonic()
                continue

            if message_type in ("vocal_features", "update"):
                if not SESSIONS[session_id]["active"]:
                    continue

                now = time.monotonic()
                last_sent = SESSIONS[session_id]["last_sent"]

                # Limit arrangement updates to avoid flooding
                # the Android app with repeated instructions.
                if now - last_sent < UPDATE_INTERVAL:
                    continue

                message["session_id"] = session_id
                arrangement = make_arrangement(message)
                await send_json(websocket, arrangement)
                SESSIONS[session_id]["last_sent"] = now
                continue

            await send_json(websocket, {
                "type": "error",
                "message": "Unknown message type"
            })

    except Exception as exc:
        print("Client error:", repr(exc))
    finally:
        SESSIONS.pop(session_id, None)
        print("Disconnected:", session_id)

async def main():
    print(f"AfriNode Live Band server listening on {HOST}:{PORT}")
    async with serve(
        handle_client,
        HOST,
        PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=1024 * 1024
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

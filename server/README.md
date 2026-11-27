# AfriNode Live Band Server

WebSocket arrangement server for the AfriNode AI Live Band project.

## Start

```bash
pip install -r requirements.txt
python app.py
```

Default port: 8765

WebSocket address:

`ws://YOUR_SERVER_IP:8765`

## Start a performance

Send:

```json
{
  "type": "start",
  "style": "Gospel",
  "key": "C",
  "chord": "C",
  "bpm": 90
}
```

## Send updated vocal features

```json
{
  "type": "vocal_features",
  "style": "Worship",
  "key": "C",
  "chord": "Am",
  "bpm": 82,
  "pitch_hz": 220,
  "confidence": 0.9
}
```

Updates are rate-limited to one arrangement every 1.5 seconds.

## Stop

```json
{"type": "stop"}
```

## Important

This server sends musical arrangement instructions as JSON.
It does not stream audio. The Android app must parse each
arrangement's `events` array and schedule MIDI notes through
its local SoundFont synthesizer.

Each event contains:
- `time_ms`: time relative to the beginning of the bar
- `duration_ms`: note duration
- `note`: MIDI note number
- `velocity`: MIDI velocity
- `instrument`: bass, keys, or lead

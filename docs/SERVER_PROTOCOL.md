# AfriNode Live Band - Server Protocol

Transport: WebSocket
Protocol: afrinode-live-band-v1

Android sends JSON messages:
- `start`
- `vocal_features`
- `stop`
- `ping`

Server returns JSON messages:
- `connected`
- `started`
- `arrangement`
- `stopped`
- `pong`
- `error`

Arrangement events are MIDI instructions, not audio samples.
Android must schedule each event at its `time_ms`, trigger the
corresponding instrument, and stop the note after `duration_ms`.
The server's event times are relative to the beginning of each bar.

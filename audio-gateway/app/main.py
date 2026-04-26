"""Audio-Gateway: Whisper ASR WebSocket Service.

Browser sendet Audio-Chunks → Whisper transkribiert → Text an Meeting-Service.
Auto-Spracherkennung inklusive.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import uuid
import wave
from collections import defaultdict
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import httpx
import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
MEETING_SERVICE_URL = os.environ.get("MEETING_SERVICE_URL", "http://meeting-service:8002")
JWKS_URL = os.environ.get("JWKS_URL", "http://auth-service:8001/.well-known/jwks.json")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "http://localhost:8001")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "nadini")

model: WhisperModel | None = None
jwks: dict | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global model, jwks
    print(f"[audio-gateway] Loading Whisper model: {WHISPER_MODEL}")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    print(f"[audio-gateway] Whisper model ready")

    # Fetch JWKS for JWT verification
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(JWKS_URL)
            resp.raise_for_status()
            jwks = resp.json()
            print(f"[audio-gateway] JWKS loaded from {JWKS_URL}")
    except Exception as exc:
        print(f"[audio-gateway] JWKS fetch failed: {exc}")

    yield


app = FastAPI(title="Nadini Audio Gateway", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nadini-audio-gateway", "model": WHISPER_MODEL}


@app.get("/edge/config")
async def edge_config():
    from app.edge import get_edge_config
    return get_edge_config()


# Audio buffer per connection
audio_buffers: dict[str, bytearray] = defaultdict(bytearray)
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 3000  # Process every 3s of audio


def verify_token(token: str) -> dict | None:
    """Verify JWT token using JWKS."""
    if not jwks:
        return None
    try:
        from jose import jwt as jose_jwt
        claims = jose_jwt.decode(token, jwks, algorithms=["RS256"],
                                  audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        if claims.get("typ") != "access":
            return None
        return claims
    except Exception:
        return None


def transcribe_audio(audio_bytes: bytes) -> list[dict]:
    """Transcribe audio bytes with Whisper. Returns list of segments."""
    if not model or len(audio_bytes) < SAMPLE_RATE:  # < 0.5s
        return []

    # Convert raw PCM16 to float32
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    segments, info = model.transcribe(
        audio_np,
        beam_size=1,
        best_of=1,
        language=None,  # Auto-detect!
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )

    results = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            results.append({
                "text": text,
                "lang": info.language,  # Auto-detected language!
                "lang_probability": round(info.language_probability, 2),
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
            })

    return results


@app.websocket("/audio/ws")
async def audio_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    meeting_id: str = Query(...),
):
    # Verify JWT
    claims = verify_token(token)
    if not claims:
        await websocket.close(code=4001, reason="Auth failed")
        return

    user_id = claims.get("sub", "")
    conn_id = str(uuid.uuid4())[:8]
    await websocket.accept()
    print(f"[audio-gateway] Client connected: {conn_id} (user={user_id[:8]})")

    buffer = bytearray()
    chunk_size = SAMPLE_RATE * 2 * (CHUNK_DURATION_MS // 1000)  # PCM16 = 2 bytes/sample

    try:
        while True:
            data = await websocket.receive_bytes()
            buffer.extend(data)

            # Process when we have enough audio
            if len(buffer) >= chunk_size:
                audio_chunk = bytes(buffer[:chunk_size])
                buffer = buffer[chunk_size:]

                # Transcribe in thread pool (Whisper is CPU-bound)
                results = await asyncio.to_thread(transcribe_audio, audio_chunk)

                for result in results:
                    # Send transcription back to client
                    await websocket.send_text(json.dumps({
                        "type": "transcription",
                        "text": result["text"],
                        "lang": result["lang"],
                        "lang_probability": result["lang_probability"],
                        "is_final": True,
                    }))

                    # Also forward to meeting-service via internal API
                    try:
                        async with httpx.AsyncClient(timeout=5) as client:
                            await client.post(
                                f"{MEETING_SERVICE_URL}/internal/transcript",
                                json={
                                    "meeting_id": meeting_id,
                                    "user_id": user_id,
                                    "text": result["text"],
                                    "lang": result["lang"],
                                },
                                headers={"X-Internal-Key": "nadini-internal"},
                            )
                    except Exception as exc:
                        print(f"[audio-gateway] Forward failed: {exc}")

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"[audio-gateway] Error: {exc}")
    finally:
        # Process remaining buffer
        if len(buffer) > SAMPLE_RATE:
            results = await asyncio.to_thread(transcribe_audio, bytes(buffer))
            for result in results:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "transcription",
                        "text": result["text"],
                        "lang": result["lang"],
                        "is_final": True,
                    }))
                except Exception:
                    pass
        print(f"[audio-gateway] Client disconnected: {conn_id}")

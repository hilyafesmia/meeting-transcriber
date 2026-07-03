"""Stage B: split the converted WAV into ~10-minute overlapping chunks.

Chunking keeps memory bounded (SPEC.md section 2/7) and gives natural
checkpoint/resume granularity for the transcription stage.
"""

from __future__ import annotations

import json
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from transcriber.errors import UserFacingError
from transcriber.workdir import STAGE_CHUNK, WorkDir

CHUNK_SECONDS = 10 * 60
OVERLAP_SECONDS = 5


@dataclass
class ChunkInfo:
    index: int
    start: float  # seconds into the full recording
    end: float
    # portion of [start, end] that is "owned" by this chunk (no overlap with
    # neighbours) -- used when stitching transcripts back together.
    owned_start: float
    owned_end: float


def _read_wav_params(wav_path: Path):
    with wave.open(str(wav_path), "rb") as wf:
        return wf.getframerate(), wf.getnframes(), wf.getsampwidth(), wf.getnchannels()


def plan_chunks(duration_seconds: float) -> list[ChunkInfo]:
    chunks: list[ChunkInfo] = []
    index = 0
    pos = 0.0
    while pos < duration_seconds:
        start = max(0.0, pos - (OVERLAP_SECONDS if index > 0 else 0))
        end = min(duration_seconds, pos + CHUNK_SECONDS + OVERLAP_SECONDS)
        owned_start = pos
        owned_end = min(duration_seconds, pos + CHUNK_SECONDS)
        chunks.append(ChunkInfo(index, start, end, owned_start, owned_end))
        pos += CHUNK_SECONDS
        index += 1
    return chunks


def split_into_chunks(work_dir: WorkDir, logger) -> list[ChunkInfo]:
    if work_dir.is_stage_done(STAGE_CHUNK) and work_dir.chunk_manifest_path.exists():
        logger.info("Tahap 2/6 (pemotongan audio) sudah selesai sebelumnya, dilewati.")
        return load_manifest(work_dir)

    wav_path = work_dir.wav_path
    if not wav_path.exists():
        raise UserFacingError(
            "Terjadi kesalahan internal: file audio hasil konversi tidak ditemukan.\n"
            "Coba jalankan ulang perintah dengan tambahan '--restart'."
        )

    framerate, nframes, sampwidth, nchannels = _read_wav_params(wav_path)
    duration = nframes / float(framerate)
    chunks = plan_chunks(duration)

    logger.info(f"Tahap 2/6: Memotong audio menjadi {len(chunks)} bagian...")

    with wave.open(str(wav_path), "rb") as src:
        for c in chunks:
            out_path = work_dir.chunk_wav_path(c.index)
            if out_path.exists():
                continue
            start_frame = int(c.start * framerate)
            end_frame = int(c.end * framerate)
            src.setpos(start_frame)
            frames = src.readframes(end_frame - start_frame)
            with wave.open(str(out_path), "wb") as dst:
                dst.setnchannels(nchannels)
                dst.setsampwidth(sampwidth)
                dst.setframerate(framerate)
                dst.writeframes(frames)

    manifest = {
        "duration_seconds": duration,
        "chunks": [asdict(c) for c in chunks],
    }
    work_dir.chunk_manifest_path.write_text(json.dumps(manifest, indent=2))
    work_dir.mark_stage_done(STAGE_CHUNK)
    logger.info("Tahap 2/6: Pemotongan audio selesai.")
    return chunks


def load_manifest(work_dir: WorkDir) -> list[ChunkInfo]:
    data = json.loads(work_dir.chunk_manifest_path.read_text())
    return [ChunkInfo(**c) for c in data["chunks"]]


def get_duration_seconds(work_dir: WorkDir) -> float:
    data = json.loads(work_dir.chunk_manifest_path.read_text())
    return data["duration_seconds"]

"""Stage C: transcribe each chunk with a quantized Whisper large-v3 (MLX).

Runs entirely offline after the one-time model download during setup.
Language is always pinned to Indonesian per SPEC.md section 5 -- never
auto-detect, since on long files auto-detect drifts and can silently
switch to translation instead of transcription.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

from transcriber.chunk import ChunkInfo
from transcriber.errors import UserFacingError
from transcriber.workdir import STAGE_TRANSCRIBE, WorkDir

MODEL_REPO = "mlx-community/whisper-large-v3-mlx-4bit"

# A segment is dropped as a hallucinated repetition loop if the same
# normalized text repeats more than this many times in a row.
MAX_CONSECUTIVE_REPEATS = 3


def _load_transcribe_fn():
    try:
        import mlx_whisper
    except ImportError:
        raise UserFacingError(
            "Modul 'mlx-whisper' belum terpasang.\n"
            "Cara memperbaiki: jalankan ulang 'setup.sh' (lihat README.md)."
        )
    return mlx_whisper.transcribe


def _dedupe_hallucinations(segments: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    run_text = None
    run_len = 0
    for seg in segments:
        norm = seg["text"].strip().lower()
        if norm and norm == run_text:
            run_len += 1
        else:
            run_text = norm
            run_len = 1
        if run_len <= MAX_CONSECUTIVE_REPEATS:
            cleaned.append(seg)
    return cleaned


def transcribe_chunks(chunks: list[ChunkInfo], work_dir: WorkDir, logger) -> None:
    pending = [c for c in chunks if not work_dir.chunk_transcript_path(c.index).exists()]

    if not pending:
        if not work_dir.is_stage_done(STAGE_TRANSCRIBE):
            work_dir.mark_stage_done(STAGE_TRANSCRIBE)
        logger.info("Tahap 3/6 (transkripsi) sudah selesai sebelumnya, dilewati.")
        return

    transcribe = _load_transcribe_fn()
    total = len(chunks)

    for c in pending:
        logger.info(
            f"Tahap 3/6: Transkripsi - bagian {c.index + 1}/{total} "
            f"({int((c.index + 1) / total * 100)}%)"
        )
        chunk_wav = work_dir.chunk_wav_path(c.index)
        if not chunk_wav.exists():
            raise UserFacingError(
                f"Terjadi kesalahan internal: bagian audio ke-{c.index + 1} hilang.\n"
                "Coba jalankan ulang perintah dengan tambahan '--restart'."
            )
        try:
            result = transcribe(
                str(chunk_wav),
                path_or_hf_repo=MODEL_REPO,
                language="id",
                task="transcribe",
                word_timestamps=False,
                condition_on_previous_text=False,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001 - convert to user-facing message
            logger.error(f"Whisper gagal pada bagian {c.index}: {exc}")
            raise UserFacingError(
                f"Transkripsi gagal pada bagian audio ke-{c.index + 1}.\n"
                f"Detail teknis sudah dicatat di: {work_dir.log_path}\n\n"
                "Cara memperbaiki: jalankan ulang perintah yang sama - proses "
                "akan melanjutkan dari bagian ini, bukan dari awal.\n"
                "Jika masalah berlanjut, kirim file log tersebut ke Claude."
            )

        segments = [
            {
                "start": c.owned_start + seg["start"],
                "end": c.owned_start + seg["end"],
                "text": seg["text"].strip(),
            }
            for seg in result.get("segments", [])
            # keep only segments inside this chunk's "owned" (non-overlap) span
            if c.owned_start <= (c.owned_start + seg["start"]) < c.owned_end
        ]
        segments = _dedupe_hallucinations(segments)

        work_dir.chunk_transcript_path(c.index).write_text(
            json.dumps(segments, ensure_ascii=False, indent=2)
        )

    work_dir.mark_stage_done(STAGE_TRANSCRIBE)
    logger.info("Tahap 3/6: Transkripsi selesai.")

    # Free Whisper before diarization loads (sequential model loading, SPEC section 7).
    gc.collect()


def load_all_transcript_segments(chunks: list[ChunkInfo], work_dir: WorkDir) -> list[dict]:
    all_segments: list[dict] = []
    for c in chunks:
        path = work_dir.chunk_transcript_path(c.index)
        if not path.exists():
            raise UserFacingError(
                f"Terjadi kesalahan internal: hasil transkripsi bagian {c.index + 1} hilang.\n"
                "Coba jalankan ulang perintah dengan tambahan '--restart'."
            )
        all_segments.extend(json.loads(path.read_text()))
    all_segments.sort(key=lambda s: s["start"])
    return all_segments

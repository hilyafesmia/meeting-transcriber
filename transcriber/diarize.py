"""Stage D: speaker diarization over the full recording (pyannote 3.1).

Runs after transcription is fully complete and Whisper has been unloaded
(sequential model loading, SPEC.md section 2/7) to keep peak memory
within the 4-8 GB budget on the target machine.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from transcriber.errors import UserFacingError
from transcriber.workdir import STAGE_DIARIZE, WorkDir

PYANNOTE_PIPELINE = "pyannote/speaker-diarization-3.1"

DEFAULT_MIN_SPEAKERS = 4
DEFAULT_MAX_SPEAKERS = 12


def get_hf_token() -> str | None:
    token = os.environ.get("HF_TOKEN")
    if token:
        return token
    token_path = Path.home() / ".cache" / "huggingface" / "token"
    if token_path.exists():
        return token_path.read_text().strip()
    return None


def _load_pipeline():
    token = get_hf_token()
    if not token:
        raise UserFacingError(
            "Token Hugging Face belum ditemukan.\n"
            "Token ini dibutuhkan sekali saja untuk mengunduh model pemisah "
            "suara pembicara (pyannote).\n\n"
            "Cara memperbaiki: jalankan ulang 'setup.sh' dan ikuti langkah "
            "'Hugging Face token' di README.md."
        )
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        raise UserFacingError(
            "Modul 'pyannote.audio' belum terpasang.\n"
            "Cara memperbaiki: jalankan ulang 'setup.sh' (lihat README.md)."
        )

    try:
        pipeline = Pipeline.from_pretrained(PYANNOTE_PIPELINE, token=token)
    except Exception as exc:  # noqa: BLE001
        raise UserFacingError(
            "Gagal memuat model pemisah suara pembicara (pyannote).\n"
            "Kemungkinan penyebab: token Hugging Face salah/kedaluwarsa, atau "
            "syarat & ketentuan model belum disetujui di halaman Hugging Face.\n\n"
            f"Detail teknis: {exc}\n\n"
            "Cara memperbaiki: jalankan 'transcribe doctor' untuk memeriksa, "
            "atau ikuti ulang langkah token di README.md."
        )

    try:
        import torch

        if torch.backends.mps.is_available():
            pipeline.to(torch.device("mps"))
    except Exception:
        pass  # CPU fallback is fine, just slower

    return pipeline


def diarize(work_dir: WorkDir, logger, min_speakers: int | None, max_speakers: int | None) -> list[dict]:
    if work_dir.is_stage_done(STAGE_DIARIZE) and work_dir.diarization_path.exists():
        logger.info("Tahap 4/6 (pemisahan suara pembicara) sudah selesai sebelumnya, dilewati.")
        return json.loads(work_dir.diarization_path.read_text())

    if not work_dir.wav_path.exists():
        raise UserFacingError(
            "Terjadi kesalahan internal: file audio hasil konversi tidak ditemukan.\n"
            "Coba jalankan ulang perintah dengan tambahan '--restart'."
        )

    logger.info(
        "Tahap 4/6: Memisahkan suara pembicara (bisa memakan waktu cukup lama)..."
    )
    pipeline = _load_pipeline()

    kwargs = {}
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers
    if not kwargs:
        kwargs = {
            "min_speakers": DEFAULT_MIN_SPEAKERS,
            "max_speakers": DEFAULT_MAX_SPEAKERS,
        }

    try:
        annotation = pipeline(str(work_dir.wav_path), **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"pyannote gagal: {exc}")
        raise UserFacingError(
            "Pemisahan suara pembicara gagal.\n"
            f"Detail teknis sudah dicatat di: {work_dir.log_path}\n\n"
            "Cara memperbaiki: jalankan ulang perintah yang sama (proses akan "
            "melanjutkan, bukan mulai dari awal). Jika masalah berlanjut, "
            "kirim file log tersebut ke Claude."
        )

    # pyannote.audio 4.x returns a DiarizeOutput with both an "as recorded"
    # annotation and an overlap-free one adapted for downstream transcription;
    # the latter is what we want when assigning one speaker per transcript segment.
    exclusive = annotation.exclusive_speaker_diarization
    turns = [
        {"start": turn.start, "end": turn.end, "label": label}
        for turn, _, label in exclusive.itertracks(yield_label=True)
    ]
    work_dir.diarization_path.write_text(json.dumps(turns, indent=2))
    work_dir.mark_stage_done(STAGE_DIARIZE)
    logger.info("Tahap 4/6: Pemisahan suara pembicara selesai.")
    return turns

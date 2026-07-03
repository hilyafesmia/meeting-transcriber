"""Stage A: convert input audio to 16 kHz mono WAV via ffmpeg (SPEC.md section 5)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from transcriber.errors import UserFacingError
from transcriber.workdir import STAGE_CONVERT, WorkDir

# Rough headroom: 16kHz mono 16-bit WAV is ~1.8 MB/min of audio.
# For a 5h recording that's ~550MB. We ask for generous headroom on top
# of that plus chunk copies, to avoid ever running out mid-run.
BYTES_PER_MINUTE_WAV = 1_800_000
HEADROOM_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


def check_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise UserFacingError(
            "ffmpeg tidak ditemukan di komputer ini.\n"
            "ffmpeg dibutuhkan untuk membaca file audio Zoom.\n\n"
            "Cara memperbaiki: jalankan ulang 'setup.sh' (lihat README.md), "
            "atau install manual dengan:\n"
            "    brew install ffmpeg"
        )


def probe_duration_seconds(input_path: Path) -> float:
    check_ffmpeg_available()
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(input_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise UserFacingError(
            "ffprobe tidak ditemukan (biasanya terpasang bersama ffmpeg).\n"
            "Cara memperbaiki: jalankan ulang 'setup.sh', atau:\n"
            "    brew install ffmpeg"
        )
    if result.returncode != 0 or not result.stdout.strip():
        raise UserFacingError(
            f"File audio tidak bisa dibaca: {input_path}\n"
            "File ini mungkin rusak, bukan file audio/video, atau formatnya "
            "tidak didukung.\n\n"
            "Cara memperbaiki: pastikan Anda memilih file 'audio.m4a' dari "
            "folder rekaman lokal Zoom, lalu coba lagi."
        )
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise UserFacingError(
            f"Durasi file audio tidak dapat dibaca: {input_path}\n"
            "Cara memperbaiki: pastikan file tidak rusak, lalu coba lagi."
        )


def check_disk_space(input_path: Path, duration_seconds: float, work_root: Path) -> None:
    estimated_wav_bytes = int((duration_seconds / 60.0) * BYTES_PER_MINUTE_WAV)
    needed = estimated_wav_bytes * 2 + HEADROOM_BYTES  # wav + chunk copies + headroom
    usage = shutil.disk_usage(work_root.parent if work_root.exists() else input_path.parent)
    if usage.free < needed:
        needed_gb = needed / (1024**3)
        free_gb = usage.free / (1024**3)
        raise UserFacingError(
            "Ruang penyimpanan (disk) tidak cukup untuk memproses rekaman ini.\n"
            f"Diperkirakan butuh sekitar {needed_gb:.1f} GB, tapi yang tersisa "
            f"hanya {free_gb:.1f} GB.\n\n"
            "Cara memperbaiki: kosongkan ruang penyimpanan (hapus file yang "
            "tidak perlu, kosongkan Sampah), lalu coba lagi."
        )


def convert_to_wav(input_path: Path, work_dir: WorkDir, logger) -> Path:
    """Convert input_path to 16kHz mono WAV, checkpointed. Returns the wav path."""
    if work_dir.is_stage_done(STAGE_CONVERT) and work_dir.wav_path.exists():
        logger.info("Tahap 1/6 (konversi audio) sudah selesai sebelumnya, dilewati.")
        return work_dir.wav_path

    check_ffmpeg_available()
    duration = probe_duration_seconds(input_path)
    if duration <= 0:
        raise UserFacingError(
            f"File audio tampak kosong (durasi 0 detik): {input_path}\n"
            "Cara memperbaiki: pastikan file rekaman benar dan tidak rusak."
        )
    work_dir.ensure_dirs()
    check_disk_space(input_path, duration, work_dir.root)

    logger.info(f"Tahap 1/6: Mengonversi audio ({duration/3600:.1f} jam)...")
    tmp_out = work_dir.wav_path.with_suffix(".wav.tmp")
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-vn",
                "-f",
                "wav",
                str(tmp_out),
            ],
            capture_output=True,
            text=True,
            timeout=None,
        )
    except FileNotFoundError:
        raise UserFacingError(
            "ffmpeg tidak ditemukan. Jalankan ulang 'setup.sh' untuk memasangnya."
        )

    if result.returncode != 0:
        logger.error(f"ffmpeg gagal: {result.stderr}")
        raise UserFacingError(
            "Gagal mengonversi file audio.\n"
            "File mungkin rusak atau bukan format audio/video yang didukung.\n\n"
            f"Detail teknis sudah dicatat di: {work_dir.log_path}\n"
            "Cara memperbaiki: coba dengan file 'audio.m4a' yang asli dari Zoom, "
            "atau kirim file log ini ke Claude untuk dibantu."
        )

    tmp_out.replace(work_dir.wav_path)
    work_dir.mark_stage_done(STAGE_CONVERT)
    logger.info("Tahap 1/6: Konversi audio selesai.")
    return work_dir.wav_path

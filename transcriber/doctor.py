"""`transcribe doctor` -- self-check for setup problems (SPEC.md section 6/9).

Prints a plain-language check-per-item report so the owner (who cannot
debug) can see what's wrong and what to do about it without help.
"""

from __future__ import annotations

import importlib
import shutil

from transcriber.diarize import get_hf_token


def _check(label: str) -> "_Check":
    return _Check(label)


class _Check:
    def __init__(self, label: str):
        self.label = label
        self.ok = False
        self.detail = ""

    def pass_(self, detail: str = "") -> "_Check":
        self.ok = True
        self.detail = detail
        return self

    def fail(self, detail: str) -> "_Check":
        self.ok = False
        self.detail = detail
        return self


def run_checks() -> tuple[bool, list[_Check]]:
    checks: list[_Check] = []

    c = _check("ffmpeg terpasang")
    if shutil.which("ffmpeg"):
        c.pass_()
    else:
        c.fail("Tidak ditemukan. Jalankan: brew install ffmpeg")
    checks.append(c)

    c = _check("Modul mlx-whisper terpasang")
    try:
        importlib.import_module("mlx_whisper")
        c.pass_()
    except ImportError:
        c.fail("Tidak ditemukan. Jalankan ulang setup.sh")
    checks.append(c)

    c = _check("Modul pyannote.audio terpasang")
    try:
        importlib.import_module("pyannote.audio")
        c.pass_()
    except ImportError:
        c.fail("Tidak ditemukan. Jalankan ulang setup.sh")
    checks.append(c)

    c = _check("Token Hugging Face tersedia")
    token = get_hf_token()
    if token:
        c.pass_()
    else:
        c.fail(
            "Tidak ditemukan. Buat token gratis di huggingface.co/settings/tokens "
            "dan simpan sesuai petunjuk di README.md"
        )
    checks.append(c)

    c = _check("Model pyannote dapat dimuat (butuh internet & token valid)")
    if token:
        try:
            from pyannote.audio import Pipeline

            Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1", token=token
            )
            c.pass_()
        except Exception as exc:  # noqa: BLE001
            c.fail(
                f"Gagal memuat model ({exc}). Pastikan sudah menyetujui syarat "
                "penggunaan model di halaman Hugging Face-nya."
            )
    else:
        c.fail("Dilewati karena token belum ada.")
    checks.append(c)

    c = _check("Ruang penyimpanan disk cukup (minimal 5 GB bebas)")
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024**3)
    if free_gb >= 5:
        c.pass_(f"{free_gb:.1f} GB bebas")
    else:
        c.fail(f"Hanya {free_gb:.1f} GB bebas. Kosongkan ruang penyimpanan.")
    checks.append(c)

    all_ok = all(c.ok for c in checks)
    return all_ok, checks


def print_report(checks: list[_Check]) -> None:
    for c in checks:
        mark = "✅" if c.ok else "❌"
        suffix = f" — {c.detail}" if c.detail else ""
        print(f"{mark} {c.label}{suffix}")

"""CLI entry point (SPEC.md section 6).

    transcribe <path>                                  full run, auto-resumes
    transcribe <path> --speakers-min N --speakers-max M override speaker bounds
    transcribe <path> --restart                        discard partial results
    transcribe doctor                                   self-check
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from shutil import which

import click

from transcriber.chunk import get_duration_seconds, split_into_chunks
from transcriber.convert import convert_to_wav
from transcriber.diarize import diarize
from transcriber.doctor import print_report, run_checks
from transcriber.errors import UserFacingError
from transcriber.merge import merge_segments_with_speakers
from transcriber.render import render_outputs
from transcriber.transcribe_stage import load_all_transcript_segments, transcribe_chunks
from transcriber.workdir import WorkDir, setup_logging

AUDIO_SUFFIXES = {".m4a", ".mp3", ".wav", ".mp4", ".aac", ".mov"}

# transcribe <path> ... has no subcommand name in front of the path, so we
# route to "run" for anything that isn't one of the real subcommands.
_KNOWN_SUBCOMMANDS = {"doctor", "run", "--help", "-h"}


class TranscribeGroup(click.Group):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] not in _KNOWN_SUBCOMMANDS:
            args = ["run", *args]
        return super().parse_args(ctx, args)


def _relaunch_under_caffeinate() -> None:
    """Re-exec this same command wrapped in caffeinate, once, so the Mac
    doesn't sleep mid-run (SPEC.md section 7)."""
    if os.environ.get("_TRANSCRIBE_CAFFEINATED") == "1" or sys.platform != "darwin":
        return
    if not which("caffeinate"):
        return
    env = os.environ.copy()
    env["_TRANSCRIBE_CAFFEINATED"] = "1"
    os.execvpe("caffeinate", ["caffeinate", "-i", sys.executable, *sys.argv], env)


def _resolve_input(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise UserFacingError(
            f"File atau folder tidak ditemukan: {path}\n"
            "Cara memperbaiki: periksa kembali lokasi file/folder, lalu coba lagi."
        )
    if path.is_dir():
        candidate = path / "audio.m4a"
        if candidate.exists():
            return candidate
        audio_files = [p for p in path.iterdir() if p.suffix.lower() in AUDIO_SUFFIXES]
        if len(audio_files) == 1:
            return audio_files[0]
        raise UserFacingError(
            f"Tidak ditemukan file 'audio.m4a' di folder: {path}\n"
            "Cara memperbaiki: pastikan Anda menunjuk ke folder rekaman lokal "
            "Zoom yang berisi 'audio.m4a', atau langsung ke file audionya."
        )
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        raise UserFacingError(
            f"Jenis file tidak dikenali: {path.name}\n"
            "Cara memperbaiki: gunakan file 'audio.m4a' dari folder rekaman "
            "lokal Zoom."
        )
    return path


@click.group(cls=TranscribeGroup, invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
def doctor() -> None:
    """Periksa kesiapan sistem (dependensi, model, token, disk)."""
    ok, checks = run_checks()
    print_report(checks)
    if ok:
        click.echo("\nSemua siap. Anda bisa mulai memakai 'transcribe <folder>'.")
    else:
        click.echo(
            "\nAda hal yang perlu diperbaiki di atas sebelum menjalankan transkripsi."
        )
        sys.exit(1)


@main.command(name="run")
@click.argument("input_path")
@click.option("--speakers-min", type=int, default=None, help="Perkiraan jumlah pembicara paling sedikit.")
@click.option("--speakers-max", type=int, default=None, help="Perkiraan jumlah pembicara paling banyak.")
@click.option("--restart", is_flag=True, default=False, help="Mulai dari awal, buang progres sebelumnya.")
def run_cmd(input_path: str, speakers_min: int | None, speakers_max: int | None, restart: bool) -> None:
    """Proses rekaman Zoom dan hasilkan transkrip (transcript.md, transcript.srt)."""
    _run_pipeline(input_path, speakers_min, speakers_max, restart)


def _run_pipeline(input_path_str: str, speakers_min: int | None, speakers_max: int | None, restart: bool) -> None:
    work_dir: WorkDir | None = None
    logger = None
    try:
        input_path = _resolve_input(input_path_str)
        input_dir = input_path.parent
        work_dir = WorkDir.for_input(input_path)

        if restart:
            work_dir.restart()
        else:
            work_dir.ensure_dirs()

        logger = setup_logging(work_dir)
        if work_dir.is_resuming() and not restart:
            click.echo("Melanjutkan proses sebelumnya yang belum selesai...")

        _relaunch_under_caffeinate()

        convert_to_wav(input_path, work_dir, logger)
        chunks = split_into_chunks(work_dir, logger)
        duration = get_duration_seconds(work_dir)
        transcribe_chunks(chunks, work_dir, logger)
        segments = load_all_transcript_segments(chunks, work_dir)
        diarization_turns = diarize(work_dir, logger, speakers_min, speakers_max)

        logger.info("Tahap 5/6: Menggabungkan transkripsi dengan pembicara...")
        turns = merge_segments_with_speakers(segments, diarization_turns)
        logger.info("Tahap 5/6: Penggabungan selesai.")

        logger.info("Tahap 6/6: Menulis hasil transkrip...")
        md_path = input_dir / "transcript.md"
        srt_path = input_dir / "transcript.srt"
        render_outputs(input_path.name, duration, turns, md_path, srt_path)
        logger.info("Tahap 6/6: Selesai.")

        work_dir.cleanup()

        click.echo("\nSelesai! Hasil transkrip tersimpan di:")
        click.echo(f"  {md_path}")
        click.echo(f"  {srt_path}")

    except UserFacingError as exc:
        click.echo(f"\n{exc.message}", err=True)
        sys.exit(1)
    except Exception:  # noqa: BLE001 - last-resort catch for unanticipated bugs
        log_hint = f"\n\nDetail teknis dicatat di: {work_dir.log_path}" if work_dir else ""
        if logger is not None:
            logger.error("Kesalahan tak terduga:\n" + traceback.format_exc())
        click.echo(
            "\nTerjadi kesalahan yang tidak terduga saat memproses rekaman."
            f"{log_hint}\n"
            "Jika masalah berlanjut, kirim file log tersebut ke Claude untuk dibantu.",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

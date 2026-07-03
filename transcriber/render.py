"""Stage F: render transcript.md, transcript.srt, and the speaker legend
(SPEC.md section 4)."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from pathlib import Path

from transcriber.merge import Turn

SAMPLE_QUOTES_PER_SPEAKER = 3
MAX_QUOTE_WORDS = 15


def _fmt_hms(seconds: float) -> str:
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_srt_time(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _shorten(text: str, max_words: int = MAX_QUOTE_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def build_speaker_legend(turns: list[Turn]) -> list[dict]:
    talk_time: dict[str, float] = defaultdict(float)
    quotes: dict[str, list[tuple[float, str]]] = defaultdict(list)

    for t in turns:
        talk_time[t.speaker] += t.end - t.start
        quotes[t.speaker].append((t.start, t.text))

    legend = []
    # order by first appearance
    seen_order = []
    for t in turns:
        if t.speaker not in seen_order:
            seen_order.append(t.speaker)

    for speaker in seen_order:
        speaker_quotes = quotes[speaker]
        n = len(speaker_quotes)
        if n <= SAMPLE_QUOTES_PER_SPEAKER:
            picks = speaker_quotes
        else:
            idxs = [0, n // 2, n - 1][:SAMPLE_QUOTES_PER_SPEAKER]
            picks = [speaker_quotes[i] for i in idxs]
        legend.append(
            {
                "speaker": speaker,
                "minutes": talk_time[speaker] / 60.0,
                "quotes": [(ts, _shorten(text)) for ts, text in picks],
            }
        )
    return legend


def render_markdown(
    source_name: str,
    processed_date: str,
    duration_seconds: float,
    turns: list[Turn],
    output_path: Path,
) -> None:
    speakers = sorted({t.speaker for t in turns})
    lines = [
        f"# Transkrip Rapat — {source_name}",
        f"- Tanggal diproses: {processed_date}",
        f"- Durasi rekaman: {_fmt_hms(duration_seconds)}",
        f"- Jumlah pembicara terdeteksi: {len(speakers)}",
        "",
        "---",
        "",
    ]
    for t in turns:
        lines.append(f"[{_fmt_hms(t.start)}] {t.speaker}: {t.text}")
        lines.append("")

    legend = build_speaker_legend(turns)
    lines.append("---")
    lines.append("")
    lines.append("## Daftar Pembicara")
    lines.append("")
    lines.append("| Label | Total bicara | Contoh |")
    lines.append("|---|---|---|")
    for entry in legend:
        quotes_str = " · ".join(
            f"[{_fmt_hms(ts)}] \"{text}\"" for ts, text in entry["quotes"]
        )
        lines.append(f"| {entry['speaker']} | {entry['minutes']:.0f} min | {quotes_str} |")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_srt(turns: list[Turn], output_path: Path) -> None:
    lines = []
    for i, t in enumerate(turns, start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_srt_time(t.start)} --> {_fmt_srt_time(t.end)}")
        lines.append(f"{t.speaker}: {t.text}")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_outputs(
    source_name: str,
    duration_seconds: float,
    turns: list[Turn],
    md_path: Path,
    srt_path: Path,
) -> None:
    processed_date = dt.date.today().isoformat()
    render_markdown(source_name, processed_date, duration_seconds, turns, md_path)
    render_srt(turns, srt_path)

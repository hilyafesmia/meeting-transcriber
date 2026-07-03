# Meeting Transcriber — Implementation Specification

**Status:** Final — all decisions below were resolved with the owner; implementation requires no further product decisions.
**Audience:** Claude Code (or any developer) implementing this tool from scratch.
**Owner profile:** Non-programmer. The owner cannot read code, debug, or interpret stack traces. Every design choice must favor robustness, self-diagnosis, and plain-language communication over flexibility or elegance.

---

## 1. Purpose

A macOS command-line tool that takes a Zoom **local recording** of a meeting held in **Bahasa Indonesia**, and produces a readable transcript with **speaker labels** and **timestamps** — processed **entirely on the local machine** (no audio ever leaves the Mac).

Meetings last **2–5 hours**. The tool must handle this reliably on modest hardware.

## 2. Target environment (hard constraints)

| Constraint | Value |
|---|---|
| Machine | MacBook Air M4, 16 GB RAM, 256 GB SSD |
| RAM budget for this tool | **4–8 GB peak** — the owner uses the Mac while it runs |
| GPU | Apple Silicon (use Metal/MPS acceleration wherever possible) |
| Thermals | Fanless — expect throttling on long runs; do not assume constant throughput |
| Network | Internet allowed **only** for one-time setup (model downloads). Normal runs must work fully offline. |

Consequences:
- Use **quantized** models (Whisper large-v3 at 4-bit/Q5, ~2–3 GB resident).
- Run pipeline stages **sequentially, never in parallel** (diarization and transcription must not be resident simultaneously). Target peak ≈ 4–5 GB.
- Never read or copy `video.mp4`. Work only from `audio.m4a`. Intermediate files go in a temp/work directory and are cleaned up on success.

## 3. Input

A Zoom local-recording folder containing:

```
audio.m4a        ← the only file used (single mixed track, all speakers blended)
video.mp4        ← ignored, never opened
recording.conf   ← ignored
```

- The user invokes the tool with a path to either the folder or the `.m4a` file directly; accept both.
- Also accept any standalone audio file (`.m4a`, `.mp3`, `.wav`, `.mp4` audio track) as a courtesy, but the Zoom folder is the primary case.
- Validate input before starting: file exists, is decodable audio, duration is sane. Fail immediately with a plain-language message if not (see §10).

## 4. Output

Written **next to the input file** (same folder):

### 4.1 `transcript.md` (primary)

Markdown, one paragraph per **speaker turn** (not per sentence), timestamp at the start of each turn:

```markdown
# Transkrip Rapat — audio.m4a
- Tanggal diproses: 2026-07-03
- Durasi rekaman: 03:41:22
- Jumlah pembicara terdeteksi: 7

---

[00:00:12] Speaker 1: Oke, kita mulai saja ya. Agenda hari ini ada tiga...

[00:01:45] Speaker 2: Sebelum itu, saya mau update dulu soal timeline
project yang kemarin kita align...

[00:02:30] Speaker 1: Silakan.
```

Rules:
- Timestamps `[HH:MM:SS]`, one per speaker turn.
- Consecutive segments from the same speaker are merged into one turn (new turn if the gap exceeds ~10 s — then repeat the label with a fresh timestamp).
- Language of transcription: Indonesian, with English terms passed through as spoken. Header/metadata labels in Indonesian are fine (owner is Indonesian).

### 4.2 Speaker legend (appended to `transcript.md`)

To support **manual renaming** (the chosen workflow — no rename tooling), append:

```markdown
---

## Daftar Pembicara

| Label | Total bicara | Contoh |
|---|---|---|
| Speaker 1 | 58 min | [00:00:12] "Oke, kita mulai saja ya..." · [01:14:02] "..." · [02:40:51] "..." |
| Speaker 2 | 41 min | [00:01:45] "Sebelum itu, saya mau update..." · ... |
```

- 2–3 sample quotes per speaker, spread across the recording (beginning / middle / end), each ≤ ~15 words.
- The owner reads/listens at those timestamps, identifies each person, then does find-and-replace by hand.

### 4.3 `transcript.srt` (secondary)

Standard SRT with per-segment timestamps and `Speaker N:` prefixes. Generated from the same data; near-zero extra cost.

## 5. Processing pipeline

Sequential stages. Each stage persists its results to the work directory before the next begins (see §7 Resume).

```
audio.m4a
  → [A] Convert: ffmpeg → 16 kHz mono WAV (~550 MB for 5 h; verify free disk first)
  → [B] Chunk: split WAV into ~10-minute chunks with small overlap (~5 s)
  → [C] Transcribe: Whisper large-v3 (quantized) per chunk, language pinned "id",
        word/segment timestamps on; save per-chunk JSON as each completes
  → [D] Diarize: pyannote speaker-diarization-3.1 over the full WAV
        (runs after ALL transcription completes and Whisper is unloaded)
  → [E] Merge: assign each transcript segment the speaker whose diarization
        turn maximally overlaps it; merge consecutive same-speaker segments;
        map raw diarization labels → "Speaker 1..N" ordered by first appearance
  → [F] Render: transcript.md + transcript.srt + legend
```

### Pinned technical choices

| Concern | Decision | Rationale |
|---|---|---|
| Language runtime | Python 3.11+, isolated venv | ecosystem for both models |
| Transcription | **mlx-whisper** with a quantized `whisper-large-v3` MLX model (4-bit community build) | Uses the M4 GPU; ~5–10× real-time; large-v3 is materially better for Indonesian than smaller models. Fallback if MLX is unworkable: whisper.cpp large-v3 Q5. |
| Language setting | **Always `language="id"`; never auto-detect** | On long files auto-detect drifts and can silently switch to translation |
| Task setting | `transcribe` (never `translate`) | |
| Diarization | **pyannote/speaker-diarization-3.1** (gated; needs HF token at setup), MPS where supported | Best local diarization quality; needed at 5–12 voices |
| Speaker bounds | Default `min_speakers=4, max_speakers=12`; CLI flags to override | Meetings have 5–8 Zoom participants but hybrid rooms add voices |
| Audio conversion | ffmpeg (bundled/installed at setup) | |
| Sleep prevention | Wrap the run in `caffeinate` (or `caffeinate -i` the own process) | Runs take 1.5–3 h |

### Anti-hallucination guards (Whisper on long meetings)

- Enable `condition_on_previous_text=False` (or equivalent) to prevent repetition loops.
- Drop segments that are exact repetitions looping > 3×, and log them.
- Silence/hold-music stretches must not produce fabricated text; use VAD-assisted chunking if available.

## 6. CLI interface

Zero-configuration by default — a normal run needs **no flags**:

```
transcribe /path/to/zoom-recording-folder
```

| Command | Behavior |
|---|---|
| `transcribe <path>` | Full run (auto-resumes if prior partial run found) |
| `transcribe <path> --speakers-min N --speakers-max M` | Override speaker bounds |
| `transcribe <path> --restart` | Discard partial results, start over |
| `transcribe doctor` | Self-check: deps installed, models present, ffmpeg works, disk space, HF token valid. Prints ✅/❌ per item with plain-language fix instructions |

Progress output must be continuous and human-readable, e.g.:

```
Tahap 2/4: Transkripsi — chunk 14/30 (46%) — perkiraan selesai ~1 jam 10 menit
```

(Indonesian or English progress text — pick one and be consistent; Indonesian preferred.)

## 7. Reliability: chunking, resume, memory

**Non-negotiable requirements:**

1. **Checkpoint after every chunk.** Per-chunk transcription results are written to the work directory (`<input folder>/.transcribe-work/`) as they complete.
2. **Automatic resume.** Rerunning the same command after a crash/interruption skips completed stages and chunks. Resume must be the default; `--restart` is the escape hatch.
3. **Sequential model loading.** Whisper is fully unloaded before pyannote loads.
4. **Disk checks up front.** Before stage A, verify enough free space (WAV + work dir ≈ 2 GB headroom); fail early with a clear message, not at hour 2.
5. **Sleep prevention** for the duration of the run.
6. **Work directory cleanup** on successful completion (keep it on failure — it's the resume state).

Expected runtime on the target machine for a 5-hour recording: **~1.5–3 hours**. The owner accepts kick-off-and-check-back / overnight runs.

## 8. Setup & installation

Owner is a non-programmer; setup must be **one command** and self-explanatory.

- Provide `setup.sh` (or an equivalent guided installer) that: installs/locates Homebrew, Python, ffmpeg; creates the venv; installs Python deps; downloads models (~4 GB total: Whisper MLX + pyannote).
- **Hugging Face token flow:** pyannote 3.1 is gated. Setup must walk the owner through it in plain language: create a free HF account → accept the model's terms on its page (give the exact URL) → create a token → paste it when prompted. Store the token locally (e.g. `~/.cache/huggingface/token`). This happens **once**; after that, all runs are offline.
- Setup ends by running `transcribe doctor` automatically and reporting readiness.
- Install a `transcribe` command on PATH (or provide an unambiguous single way to invoke it).

**Optional (nice-to-have, after CLI works):** a drag-and-drop wrapper (Automator/Shortcuts droplet or `.app` stub) that runs `transcribe` on a dropped folder and shows progress in a Terminal window. Explicitly out of scope: any windowed GUI.

## 9. Error handling & diagnostics (first-class requirement)

The owner **cannot debug**. Therefore:

- Every anticipated failure (missing file, undecodable audio, out of disk, out of memory, missing model, invalid HF token, no internet during setup) must produce a **plain-language message that says what happened and exactly what to do next**. Never show a raw Python traceback as the primary output.
- All runs write a detailed log to `.transcribe-work/run.log`. Every error message ends with: *"Jika masalah berlanjut, kirim file log ini ke Claude: <path>"* — the log is the owner's debugging interface (they paste it into a Claude session).
- Out-of-memory strategy: if a stage is killed/fails on memory, on resume automatically retry that stage in a lower-memory mode (smaller batch / more aggressive quantization) rather than failing permanently.
- `transcribe doctor` must be able to detect and explain every setup-level problem.

## 10. Known limitations (documented for the owner, not to be "fixed")

State these in the README:

1. **Speaker accuracy at 5–12 voices is imperfect.** Overlapping speech gets mislabeled; similar voices may merge or one voice may split into two labels. The legend + manual renaming workflow absorbs this.
2. **Hybrid-room audio is worse.** People sharing one room mic (far-field, echo) will have noticeably lower transcription and diarization accuracy than headset participants. Upside: diarization separates by *voice*, so multiple people behind one Zoom name do get distinct labels.
3. **Heavy code-switching and regional languages** (full English sentences, Javanese, Sundanese, bahasa gaul) will have elevated error rates. Embedded English *terms* generally pass through fine.
4. Speaker labels are anonymous (`Speaker N`); naming is manual by design.
5. Processing is slow by design (hours, not minutes) — the trade for local, private, maximum-accuracy processing on a fanless laptop.

## 11. Acceptance criteria

Claude must verify these before declaring the tool done:

1. `setup.sh` on a machine meeting §2 ends with `doctor` reporting all ✅.
2. `transcribe` on a real Zoom local-recording folder produces `transcript.md` and `transcript.srt` matching §4 formats, including the legend.
3. Timestamps are monotonically increasing and within ±2 s of the audio at spot-checks.
4. Indonesian transcription quality sanity check on a sample: read a few segments against the audio.
5. **Resume test:** kill the process mid-transcription; rerun; it resumes from the last completed chunk and finishes; output is complete and well-formed.
6. **Memory test:** peak RSS across the run stays within ~5 GB.
7. A wrong path, a non-audio file, and a missing model each produce plain-language errors per §9 (no raw tracebacks).
8. A run with Wi-Fi disabled (after setup) completes successfully.

## 12. Out of scope

- Live/real-time transcription; joining meetings; anything cloud.
- Summaries, action items, translation (the Markdown output is deliberately LLM-paste-friendly if the owner wants this later).
- Windowed GUI; speaker-rename tooling; batch/queue processing of multiple recordings.
- Editing or processing `video.mp4`.

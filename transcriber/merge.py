"""Stage E: assign speakers to transcript segments and build speaker turns.

For each transcript segment, pick the diarization turn with maximum
temporal overlap. Consecutive segments assigned to the same speaker are
merged into a single "turn" (SPEC.md section 4: timestamps are per turn,
not per sentence). Raw diarization labels (e.g. "SPEAKER_00") are
remapped to "Speaker 1..N" ordered by first appearance.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_GAP_SECONDS = 10.0  # new turn if silence between same-speaker segments exceeds this


@dataclass
class Turn:
    speaker: str
    start: float
    end: float
    text: str


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _assign_speaker(segment: dict, diarization_turns: list[dict]) -> str:
    best_label = "UNKNOWN"
    best_overlap = 0.0
    for turn in diarization_turns:
        ov = _overlap(segment["start"], segment["end"], turn["start"], turn["end"])
        if ov > best_overlap:
            best_overlap = ov
            best_label = turn["label"]
    return best_label


def merge_segments_with_speakers(
    segments: list[dict], diarization_turns: list[dict]
) -> list[Turn]:
    labeled = []
    for seg in segments:
        if not seg["text"].strip():
            continue
        label = _assign_speaker(seg, diarization_turns)
        labeled.append((label, seg))

    # remap raw labels -> "Speaker N" by first appearance
    label_map: dict[str, str] = {}
    next_num = 1
    for label, _ in labeled:
        if label not in label_map:
            label_map[label] = f"Speaker {next_num}"
            next_num += 1

    turns: list[Turn] = []
    for label, seg in labeled:
        speaker = label_map[label]
        if (
            turns
            and turns[-1].speaker == speaker
            and seg["start"] - turns[-1].end <= MAX_GAP_SECONDS
        ):
            turns[-1].end = seg["end"]
            turns[-1].text = f"{turns[-1].text} {seg['text']}".strip()
        else:
            turns.append(Turn(speaker=speaker, start=seg["start"], end=seg["end"], text=seg["text"]))

    return turns

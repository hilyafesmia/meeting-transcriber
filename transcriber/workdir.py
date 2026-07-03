"""Work directory & checkpoint management (SPEC.md section 7).

Layout inside `<input folder>/.transcribe-work/`:

    run.log                 - full log for every run (appended)
    audio_16k.wav            - converted audio (stage A output)
    chunks/
        chunk_0000.wav
        chunk_0001.wav
        ...
        manifest.json         - chunk boundaries (start/end seconds, overlap)
    transcripts/
        chunk_0000.json        - whisper output for this chunk
        chunk_0001.json
        ...
    diarization.json          - pyannote turns for the whole file
    stage.json                - {"completed_stages": ["convert", "chunk", ...]}

Resume rule: a stage is considered done if its expected output files
exist AND stage.json lists it as completed. `--restart` wipes the whole
work directory before starting.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


def _safe_name(name: str) -> str:
    """Turn an arbitrary filename into a safe work-directory component."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)

STAGE_CONVERT = "convert"
STAGE_CHUNK = "chunk"
STAGE_TRANSCRIBE = "transcribe"
STAGE_DIARIZE = "diarize"
STAGE_MERGE = "merge"
STAGE_RENDER = "render"

ALL_STAGES = [
    STAGE_CONVERT,
    STAGE_CHUNK,
    STAGE_TRANSCRIBE,
    STAGE_DIARIZE,
    STAGE_MERGE,
    STAGE_RENDER,
]


@dataclass
class WorkDir:
    root: Path

    @classmethod
    def for_input(cls, input_path: Path) -> "WorkDir":
        """One work directory per *input file*, not per folder -- two
        different recordings in the same folder must never share state."""
        return cls(
            root=input_path.parent / ".transcribe-work" / _safe_name(input_path.name)
        )

    # --- paths -----------------------------------------------------

    @property
    def wav_path(self) -> Path:
        return self.root / "audio_16k.wav"

    @property
    def chunks_dir(self) -> Path:
        return self.root / "chunks"

    @property
    def chunk_manifest_path(self) -> Path:
        return self.chunks_dir / "manifest.json"

    @property
    def transcripts_dir(self) -> Path:
        return self.root / "transcripts"

    @property
    def diarization_path(self) -> Path:
        return self.root / "diarization.json"

    @property
    def stage_state_path(self) -> Path:
        return self.root / "stage.json"

    @property
    def log_path(self) -> Path:
        return self.root / "run.log"

    def chunk_wav_path(self, index: int) -> Path:
        return self.chunks_dir / f"chunk_{index:04d}.wav"

    def chunk_transcript_path(self, index: int) -> Path:
        return self.transcripts_dir / f"chunk_{index:04d}.json"

    # --- lifecycle ---------------------------------------------------

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def restart(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.ensure_dirs()

    def cleanup(self) -> None:
        """Remove the work directory after a fully successful run."""
        if self.root.exists():
            shutil.rmtree(self.root)

    # --- stage completion tracking ------------------------------------

    def _read_state(self) -> dict:
        if not self.stage_state_path.exists():
            return {"completed_stages": []}
        try:
            return json.loads(self.stage_state_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {"completed_stages": []}

    def _write_state(self, state: dict) -> None:
        self.stage_state_path.write_text(json.dumps(state, indent=2))

    def is_stage_done(self, stage: str) -> bool:
        return stage in self._read_state().get("completed_stages", [])

    def mark_stage_done(self, stage: str) -> None:
        state = self._read_state()
        completed = state.setdefault("completed_stages", [])
        if stage not in completed:
            completed.append(stage)
        self._write_state(state)

    def is_resuming(self) -> bool:
        """True if there is prior partial (or complete) progress to resume from."""
        return self.root.exists() and self.stage_state_path.exists()


def setup_logging(work_dir: WorkDir) -> logging.Logger:
    work_dir.ensure_dirs()
    logger = logging.getLogger("transcriber")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    file_handler = logging.FileHandler(work_dir.log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)
    return logger

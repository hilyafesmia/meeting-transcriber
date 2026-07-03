# Meeting Transcriber

This tool turns a Zoom recording (in Bahasa Indonesia) into a readable
transcript that shows **who said what** and **when**, complete with
timestamps. Everything runs on your own Mac — your audio is never
uploaded anywhere.

This guide assumes you have **never used a programming tool before**.
It explains every step, including things that might feel obvious to a
programmer, like what "Terminal" is and how to paste a command. Take it
one step at a time — you don't need to understand *why* each step
works, just follow along.

---

## Table of contents

1. [What this tool does](#what-this-tool-does)
2. [What you need before starting](#what-you-need-before-starting)
3. [Step 1 — Open Terminal](#step-1--open-terminal)
4. [Step 2 — Run the one-time setup](#step-2--run-the-one-time-setup)
5. [Step 3 — Create your free Hugging Face account and token](#step-3--create-your-free-hugging-face-account-and-token)
6. [Step 4 — Check that everything is ready](#step-4--check-that-everything-is-ready)
7. [Step 5 — Transcribe a recording](#step-5--transcribe-a-recording)
8. [Understanding the output](#understanding-the-output)
9. [If something goes wrong](#if-something-goes-wrong)
10. [Other things you can do](#other-things-you-can-do)
11. [Known limitations](#known-limitations)
12. [System requirements](#system-requirements)

---

## What this tool does

You give it a Zoom recording. It gives you back a text file that reads
like a script of the meeting:

```
[00:00:12] Speaker 1: Oke, kita mulai saja ya. Agenda hari ini ada tiga...
[00:01:45] Speaker 2: Sebelum itu, saya mau update dulu soal timeline...
```

- **Timestamps** (`[00:01:45]`) so you can jump back to the recording
  and find that exact moment.
- **Speaker labels** ("Speaker 1", "Speaker 2", etc.) so you can tell
  who was talking, even though the tool doesn't know their real names
  yet (more on that below).
- Everything happens **on your computer**. Nothing about your meeting
  — not the audio, not the words spoken — is sent to the internet,
  except for a one-time download of the AI models themselves (which
  is just software, not your data).

It is slow on purpose — a several-hour meeting can take **1 to 3
hours** to process — because it is doing all this work locally on your
laptop instead of on someone else's expensive server. You start it and
walk away; you don't need to watch it work.

---

## What you need before starting

- A **Mac with Apple Silicon** (an M1, M2, M3, or M4 chip — this
  includes basically all Macs sold since late 2020). If you're not
  sure, click the Apple logo (top-left of your screen) → **About This
  Mac**. It will say "Chip: Apple M1/M2/M3/M4..." — if it instead says
  "Intel", this tool will still technically work but will be very slow
  and is not recommended.
- At least **5 GB of free disk space** (ideally more). To check:
  Apple logo → **About This Mac** → **Storage**.
- An **internet connection** for the one-time setup (after that, you
  can process recordings completely offline).
- A **Zoom local recording folder**. This is the folder Zoom creates
  on your own computer when you record a meeting locally (not a "cloud
  recording"). It contains three files: `audio.m4a`, `video.mp4`, and
  `recording.conf`. This tool only needs `audio.m4a`.
- About **10-15 minutes of your time** for the one-time setup (plus
  waiting time for downloads, which you can do something else during).

---

## Step 1 — Open Terminal

"Terminal" is an app that lets you type commands directly to your Mac,
instead of clicking icons. It looks intimidating the first time, but
you'll only ever need to copy-paste the commands below — you don't
need to understand them.

1. Press **Cmd + Space** to open Spotlight search.
2. Type `Terminal` and press **Enter**.
3. A window opens with a black or white background and some text
   ending in a `%` or `$` sign, followed by a blinking cursor. This is
   where you'll type or paste commands.

Keep this window open — you'll use it for every step below.

**How to run a command:** throughout this guide, you'll see instructions
in a box like this:

```
transcribe doctor
```

To run it: click inside the Terminal window, type or paste the text
exactly as shown, then press **Enter**. Pasting: copy the text
normally (select it, Cmd+C), click into Terminal, then press **Cmd+V**
and **Enter**.

---

## Step 2 — Run the one-time setup

This step installs everything the tool needs: a few small helper
programs, and about 4 GB of AI models. You only do this once.

1. In Terminal, navigate to the folder where this tool lives. If this
   folder is at, for example, `/Users/hilyahilya/Documents/meeting-transcriber`,
   type:

   ```
   cd /Users/hilyahilya/Documents/meeting-transcriber
   ```

   (`cd` means "change directory" — it just tells Terminal where to
   look next.)

2. Run the setup script:

   ```
   ./setup.sh
   ```

3. Watch the output. This step will:
   - Install **Homebrew** (a package manager for Mac — think of it as
     an App Store for command-line tools) if you don't have it.
   - Install **ffmpeg** (a tool for reading audio/video files).
   - Install **pyenv** (a tool for managing Python versions) and set up
     an isolated Python environment just for this tool, so it can't
     interfere with anything else on your Mac.
   - Download and install the AI models (**this is the slow part** —
     expect several minutes depending on your internet speed, since
     it's a few gigabytes).
   - Pause partway through to ask you to set up a **Hugging Face
     token** — see Step 3 below, which explains exactly what to do
     when you reach this point.
   - Finish by running a **readiness check** and telling you if
     anything is still missing.

4. If your Mac shows a popup asking for your password (this can happen
   during the Homebrew install step), type your normal Mac login
   password and press Enter. Nothing will appear on screen as you
   type — that's normal, just type it and press Enter.

If this step gets interrupted or you need to run it again for any
reason, that's safe — just run `./setup.sh` again. It checks what's
already installed and skips it.

---

## Step 3 — Create your free Hugging Face account and token

**Why this is needed:** the part of this tool that figures out *who is
speaking* (as opposed to just transcribing the words) uses a
best-in-class AI model made by a research group called "pyannote".
That model is free to use, but the website that hosts it (Hugging
Face) requires a free account and requires you to click "I agree" on
a couple of pages before you can download it. This is a one-time,
5-minute task. **Your meeting audio is never uploaded to Hugging Face**
— this token is only used to download the AI model files to your own
computer.

When `./setup.sh` reaches this step, it will pause and print
instructions in the Terminal. Do the following, in a web browser (not
Terminal):

1. **Create a free account** (if you don't already have one):
   👉 https://huggingface.co/join

2. **Visit this page and accept the terms**, so you're allowed to
   download the model:
   👉 https://huggingface.co/pyannote/speaker-diarization-3.1

   Log in if it asks you to, then look for a button or box that says
   something like **"Agree and access repository"** and click it.

3. **Visit this second page and do the same thing**:
   👉 https://huggingface.co/pyannote/segmentation-3.0

4. **Visit this third page and do the same thing**:
   👉 https://huggingface.co/pyannote/speaker-diarization-community-1

   (This one is required by a newer version of the software and isn't
   optional — please don't skip it, or diarization will fail later
   with a permissions error.)

5. **Create an access token**:
   👉 https://huggingface.co/settings/tokens

   Click **"Create new token"**. Give it any name you like (e.g.
   "meeting-transcriber"). For the token type/role, choose **"Read"**
   (you don't need "Write" access). Click **Create token**.

6. A long string of letters and numbers will appear, starting with
   something like `hf_...`. Click the **copy** button next to it.
   **This is your token — treat it like a password.** You won't be
   able to see it again after leaving this page (though you can always
   create a new one if needed).

7. Go back to Terminal, where `./setup.sh` should be waiting with a
   prompt like:

   ```
   Tempelkan token Anda di sini, lalu tekan Enter:
   ```

   (This means "Paste your token here, then press Enter.") Paste your
   token (Cmd+V) and press **Enter**.

   If Terminal isn't waiting for you anymore because too much time
   passed, that's fine — just run `./setup.sh` again, and it will ask
   for the token again.

   **If you'd rather not type your token into a prompt at all**, you
   can save it yourself instead. Run this in Terminal, replacing the
   placeholder with your real token:

   ```
   mkdir -p ~/.cache/huggingface
   echo -n "PASTE_YOUR_TOKEN_HERE" > ~/.cache/huggingface/token
   ```

Once this is done, setup will finish automatically and run a readiness
check.

---

## Step 4 — Check that everything is ready

At any time, you can check whether your Mac is properly set up by
running:

```
transcribe doctor
```

You'll see a list like this:

```
✅ ffmpeg terpasang
✅ Modul mlx-whisper terpasang
✅ Modul pyannote.audio terpasang
✅ Token Hugging Face tersedia
✅ Model pyannote dapat dimuat (butuh internet & token valid)
✅ Ruang penyimpanan disk cukup (minimal 5 GB bebas)

Semua siap. Anda bisa mulai memakai 'transcribe <folder>'.
```

(The messages are in Indonesian since that's the tool's primary
audience, but every ✅/❌ is self-explanatory, and any ❌ comes with
plain instructions on how to fix it — e.g. "Jalankan ulang setup.sh"
means "Run setup.sh again".)

If everything shows ✅, you're ready to transcribe a real recording.
If anything shows ❌, follow the instruction next to it, then run
`transcribe doctor` again to confirm.

---

## Step 5 — Transcribe a recording

1. Find your Zoom **local recording folder** on your Mac. By default,
   Zoom saves these inside a folder called `zoom` in your Documents
   folder, in a subfolder named after the meeting date/time. Inside,
   you should see `audio.m4a`, `video.mp4`, and `recording.conf`.

2. In Terminal, run:

   ```
   transcribe /path/to/your/zoom-recording-folder
   ```

   **The easiest way to get the exact path:** in Terminal, type
   `transcribe ` (with a trailing space, don't press Enter yet), then
   find that folder in Finder and **drag the folder icon directly into
   the Terminal window**. Its full path will be typed in automatically.
   Then press Enter.

3. The tool will print progress like:

   ```
   Tahap 1/6: Mengonversi audio...
   Tahap 2/6: Memotong audio menjadi 12 bagian...
   Tahap 3/6: Transkripsi - bagian 4/12 (33%)
   ...
   ```

   ("Tahap" means "Stage" — you'll see it count from 1 to 6 as it
   works through: converting the audio, splitting it into pieces,
   transcribing the words, figuring out who's speaking, combining the
   two, and writing the final files.)

4. **Just leave it running.** For a long meeting (several hours), this
   can take **1 to 3 hours**. You can:
   - Let the screen go to sleep / turn off the display — that's fine.
   - Use your computer for other light tasks (browsing, writing) — it
     may just run a bit slower.
   - **Do not close the laptop lid** and **do not shut down or restart
     the Mac** while it's running, or the process will stop.

5. When it's done, you'll see:

   ```
   Selesai! Hasil transkrip tersimpan di:
     /path/to/your/zoom-recording-folder/transcript.md
     /path/to/your/zoom-recording-folder/transcript.srt
   ```

   ("Selesai!" means "Done!") Your transcript is ready in that same
   folder.

### If it stops partway through

If your Mac restarts, the process crashes, or you accidentally close
Terminal, don't worry — no progress is lost. Just run the **exact same
command again**:

```
transcribe /path/to/your/zoom-recording-folder
```

You'll see:

```
Melanjutkan proses sebelumnya yang belum selesai...
```

("Continuing the previous unfinished process...") It will pick up
close to where it left off, instead of starting over from zero.

If you ever want to throw away progress and start completely fresh on
the same recording, add `--restart`:

```
transcribe /path/to/your/zoom-recording-folder --restart
```

### If you know roughly how many people spoke

By default, the tool assumes somewhere between 4 and 12 speakers. If
you know the actual number (or a rough range), telling it helps
accuracy:

```
transcribe /path/to/your/zoom-recording-folder --speakers-min 5 --speakers-max 8
```

---

## Understanding the output

Two files appear in the same folder as your recording:

- **`transcript.md`** — the main transcript. Open it with any text
  editor (double-clicking it should open TextEdit, or you can use
  something like Visual Studio Code, Notion, or even paste it into
  Google Docs). It contains:
  - A short header with the date processed, recording length, and
    number of speakers detected.
  - The full transcript, one paragraph per turn someone speaks, each
    starting with a timestamp and a speaker label, e.g.:
    ```
    [00:14:22] Speaker 3: oke, kita mulai dari update tim finance...
    ```
  - A **"Daftar Pembicara"** ("Speaker list") section at the very
    bottom — a table showing how much each speaker talked and 2-3
    sample quotes with timestamps for each one. Use this to figure out
    who's who (e.g. "Speaker 3 sounds like it's Budi, based on that
    quote"), then use your text editor's Find & Replace to swap
    "Speaker 3" for "Budi" throughout the whole document.

- **`transcript.srt`** — the same content in "subtitle" format, useful
  if you ever want to overlay the transcript as captions on the
  `video.mp4` file using a video editor. Most people can ignore this
  file.

**Speaker labels are always anonymous** ("Speaker 1", "Speaker 2",
etc.) — the tool has no way to know real names on its own. Renaming
them is a manual, one-time step you do yourself using the speaker list
described above.

---

## If something goes wrong

Every error message this tool shows is written in plain language and
tells you what to do next. For example:

```
Ruang penyimpanan (disk) tidak cukup untuk memproses rekaman ini.
Cara memperbaiki: kosongkan ruang penyimpanan...
```

("Not enough disk space. How to fix it: free up storage space...")

If an error message isn't enough to resolve on your own, every attempt
also writes a detailed technical log file, mentioned in the error
message itself, at a path like:

```
/path/to/your/zoom-recording-folder/.transcribe-work/<recording name>/run.log
```

**You can share this log file with Claude (or whoever is helping you)
to get help.** It contains technical details but no need to understand
them yourself — just pass the file along.

---

## Other things you can do

- **Check readiness at any time:**
  ```
  transcribe doctor
  ```
- **Get a reminder of all commands:**
  ```
  transcribe --help
  ```

---

## Known limitations

It's worth knowing what this tool is *not* good at, so you're not
surprised:

1. **Speaker labels aren't perfect**, especially with 5+ people
   talking. If two people talk over each other, or two people sound
   similar, the tool can mislabel who said what, or occasionally split
   one person into two different labels. This is why the speaker list
   + manual renaming step exists — it's designed around this
   limitation, not despite it.
2. **Hybrid meetings (some people in a room sharing one microphone,
   others on their own headsets) are harder.** People far from a
   shared microphone will have lower transcription accuracy due to
   echo and background noise. The upside: since the tool listens to
   *voices*, not Zoom account names, it can usually tell apart several
   people sharing one Zoom name in a conference room.
3. **Heavy language-mixing lowers accuracy.** Indonesian sentences with
   the occasional English word or phrase mixed in (very common in
   business meetings) work well. Full sentences in English, Javanese,
   Sundanese, or casual slang will have more mistakes.
4. **It's slow, on purpose.** A multi-hour meeting can take 1-3 hours
   to process. This is the tradeoff for running entirely on your own
   laptop, privately, instead of uploading your meeting to a company's
   servers.

---

## System requirements

- A Mac with an Apple Silicon chip (M1 or newer). Recommended: 16 GB
  of RAM.
- About 4-5 GB of free disk space for the AI models, plus roughly
  2 GB of temporary space for every 5 hours of recording you process
  (this is cleaned up automatically after each successful run).
- A Zoom **local recording** (not a cloud recording) containing an
  `audio.m4a` file — a single mixed audio track with everyone's voice
  combined (not separate files per participant).

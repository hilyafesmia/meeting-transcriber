# Meeting Transcriber

Mengubah rekaman lokal Zoom (Bahasa Indonesia) menjadi transkrip dengan
label pembicara dan penanda waktu -- semuanya diproses di komputer Anda
sendiri, tanpa mengunggah audio ke mana pun.

Lihat [SPEC.md](SPEC.md) untuk spesifikasi teknis lengkap.

## Pasang sekali saja

```
./setup.sh
```

Script ini akan:
1. Memasang Homebrew, ffmpeg, dan pyenv jika belum ada.
2. Membuat Python virtualenv khusus untuk tool ini.
3. Memasang semua paket yang dibutuhkan (mengunduh sekitar 4 GB model).
4. Memandu Anda membuat token Hugging Face (sekali saja -- lihat di bawah).
5. Menjalankan pemeriksaan kesiapan sistem di akhir.

Butuh internet hanya untuk langkah ini. Setelah setup selesai, semua
proses transkripsi berjalan sepenuhnya offline.

### Token Hugging Face (kenapa dibutuhkan)

Model pemisah suara pembicara terbaik yang bisa berjalan lokal
(`pyannote/speaker-diarization-3.1`) mengharuskan akun gratis Hugging
Face untuk mengunduhnya sekali. Audio Anda tetap tidak pernah diunggah
ke mana pun -- token ini hanya untuk mengunduh model ke komputer Anda.
`setup.sh` akan memandu langkah ini.

## Memakai

Siapkan folder rekaman lokal Zoom (berisi `audio.m4a`, `video.mp4`,
`recording.conf`), lalu jalankan:

```
transcribe /path/ke/folder-rekaman-zoom
```

Hasilnya akan muncul di folder yang sama:
- `transcript.md` -- transkrip lengkap dengan label pembicara, penanda
  waktu, dan daftar pembicara di akhir untuk membantu Anda mengganti
  "Speaker 1", "Speaker 2", dst. menjadi nama asli.
- `transcript.srt` -- format subtitle, jika dibutuhkan.

Proses ini memakan waktu lama untuk rekaman panjang -- perkirakan
**1.5 sampai 3 jam untuk rekaman 5 jam**. Anda bisa menjalankannya lalu
meninggalkan komputer (layar boleh mati, tapi jangan tutup laptop).

### Jika prosesnya terhenti

Jika komputer mati, tidur, atau proses berhenti karena sebab apa pun,
jalankan perintah yang sama persis lagi:

```
transcribe /path/ke/folder-rekaman-zoom
```

Proses akan **melanjutkan** dari titik terakhir, bukan mulai dari awal.

Untuk memulai ulang dari nol (membuang progres sebelumnya):

```
transcribe /path/ke/folder-rekaman-zoom --restart
```

### Mengatur perkiraan jumlah pembicara

Secara default, tool ini menebak antara 4-12 pembicara. Jika Anda tahu
kisaran jumlah pembicara sebenarnya, ini membantu akurasi:

```
transcribe /path/ke/folder-rekaman-zoom --speakers-min 5 --speakers-max 9
```

### Memeriksa kesiapan sistem

```
transcribe doctor
```

Menampilkan daftar centang (✅/❌) untuk setiap komponen yang dibutuhkan,
dengan instruksi perbaikan jika ada yang bermasalah.

## Jika terjadi error

Setiap pesan error akan menjelaskan apa yang salah dan apa yang harus
dilakukan. Jika masalah berlanjut, setiap folder kerja punya file log
lengkap di:

```
<folder rekaman>/.transcribe-work/run.log
```

Kirim file log ini ke Claude untuk dibantu.

## Keterbatasan yang perlu diketahui

1. **Akurasi label pembicara tidak sempurna** pada rapat dengan 5-12+
   suara. Ucapan yang bertumpang tindih bisa salah label; suara yang
   mirip kadang tergabung atau malah terpecah jadi dua label berbeda.
   Gunakan daftar pembicara di akhir `transcript.md` untuk mengganti
   nama secara manual.
2. **Audio rapat hybrid (beberapa orang berbagi satu mikrofon/laptop)
   kualitasnya lebih rendah** dibanding peserta yang pakai headset --
   suara dari jarak jauh, gema, dan tumpang tindih membuat transkripsi
   dan pemisahan suara kurang akurat. Sisi baiknya: karena pemisahan
   dilakukan berdasarkan suara (bukan nama akun Zoom), beberapa orang
   di balik satu nama Zoom tetap bisa mendapat label berbeda.
3. **Campuran bahasa yang berat** (kalimat penuh dalam Bahasa Inggris,
   Bahasa Jawa, Bahasa Sunda, atau bahasa gaul) akan punya tingkat
   kesalahan lebih tinggi. Istilah Bahasa Inggris yang diselipkan di
   kalimat Indonesia umumnya tetap terbaca baik.
4. Label pembicara bersifat anonim ("Speaker 1", dst.) -- pemberian
   nama asli dilakukan manual, sesuai desain.
5. Proses ini memang lambat (berjam-jam, bukan menit) -- ini adalah
   konsekuensi dari memproses secara lokal, privat, dan seakurat
   mungkin di laptop tanpa kipas (fanless).

## Kebutuhan sistem

- Mac Apple Silicon (M1 atau lebih baru), disarankan 16 GB RAM.
- Sekitar 4-5 GB ruang disk bebas untuk model, ditambah ruang untuk
  file audio sementara (sekitar 2 GB per 5 jam rekaman).
- Rekaman lokal Zoom (bukan rekaman cloud) dengan file `audio.m4a`
  (audio tercampur, bukan per-peserta).

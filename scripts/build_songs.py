#!/usr/bin/env python3
"""
Comprime tutti gli mp3 in audio_src/ (bitrate basso, mono, adatto allo
speaker del watch) salvandoli in audio/, e rigenera songs.json.

- Il titolo è il nome del file sorgente (senza estensione, spazi mantenuti).
- Il nome file di output ha gli spazi sostituiti da underscore.
- L'hash è sequenziale: i brani già presenti in songs.json mantengono il
  loro hash (per non forzare un ri-download inutile sul watch), solo i
  brani nuovi ricevono il prossimo numero libero.

Parametri di compressione: 96kbps, mono, 32kHz — adeguati per lo speaker
di un Amazfit Bip Max, drasticamente più piccoli del sorgente originale.
"""

import json
import subprocess
import sys
from pathlib import Path

SRC_DIR = Path("audio_src")
OUT_DIR = Path("audio")
SONGS_JSON = Path("songs.json")

# Parametri di compressione ffmpeg
AUDIO_BITRATE = "48k"
AUDIO_CHANNELS = "1"  # mono
AUDIO_SAMPLE_RATE = "32000"


def load_existing_hashes():
    """Legge songs.json esistente per riusare gli hash già assegnati."""
    existing = {}
    max_hash = 0

    if SONGS_JSON.exists():
        try:
            data = json.loads(SONGS_JSON.read_text(encoding="utf-8"))
            for song in data.get("songs", []):
                file_name = Path(song["file"]).name
                existing[file_name] = song["hash"]
                try:
                    max_hash = max(max_hash, int(song["hash"]))
                except (ValueError, TypeError):
                    pass
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Attenzione: songs.json esistente non leggibile ({e}), verrà ricreato.")

    return existing, max_hash


def compress_audio(src_path: Path, dst_path: Path):
    """Ricomprime un file audio con ffmpeg."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",  # sovrascrivi output se esiste
        "-i", str(src_path),
        "-b:a", AUDIO_BITRATE,
        "-ac", AUDIO_CHANNELS,
        "-ar", AUDIO_SAMPLE_RATE,
        str(dst_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERRORE ffmpeg su {src_path}:\n{result.stderr}")
        sys.exit(1)


def main():
    if not SRC_DIR.exists():
        print(f"Cartella '{SRC_DIR}' non trovata. Niente da fare.")
        return

    mp3_files = sorted(SRC_DIR.glob("*.mp3"))
    if not mp3_files:
        print(f"Nessun file .mp3 trovato in '{SRC_DIR}'.")
        return

    existing_hashes, max_hash = load_existing_hashes()
    OUT_DIR.mkdir(exist_ok=True)

    songs = []

    for src_path in mp3_files:
        original_name = src_path.name
        title = src_path.stem  # nome senza estensione, spazi mantenuti
        safe_name = original_name.replace(" ", "_")
        dst_path = OUT_DIR / safe_name

        print(f"Comprimo: {original_name} -> audio/{safe_name}")
        compress_audio(src_path, dst_path)

        if safe_name in existing_hashes:
            song_hash = existing_hashes[safe_name]
        else:
            max_hash += 1
            song_hash = str(max_hash)
            print(f"  Nuovo brano rilevato (hash {song_hash})")

        song_id = Path(safe_name).stem

        songs.append({
            "id": song_id,
            "name": title,
            "file": f"audio/{safe_name}",
            "hash": song_hash,
        })

    output = {"songs": songs}
    SONGS_JSON.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nsongs.json aggiornato con {len(songs)} brani totali.")


if __name__ == "__main__":
    main()

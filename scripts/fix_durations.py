import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
PODCASTS_DIR = REPO_ROOT / "podcasts"
RSS_INGEST_DIR = Path(__file__).resolve().parent / "rss_ingest"


def log(message: str) -> None:
    print(message)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
            json.dump(data, tmp_file, indent=4, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def resolve_audio_path(local_audio: Any) -> Optional[Path]:
    if not isinstance(local_audio, str) or not local_audio.strip():
        return None

    raw = local_audio.strip()
    candidates: list[Path] = []

    direct = Path(raw)
    candidates.append(direct)

    if not direct.is_absolute():
        candidates.append(REPO_ROOT / direct)

    if raw.startswith("/home/thomas/hechicero/"):
        rel = PurePosixPath(raw).relative_to("/home/thomas/hechicero")
        candidates.append(REPO_ROOT.joinpath(*rel.parts))

    if raw.startswith("/"):
        rel_from_root = PurePosixPath(raw.lstrip("/"))
        candidates.append(REPO_ROOT.joinpath(*rel_from_root.parts))

    seen = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def probe_duration_seconds(audio_path: Path) -> Optional[int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise RuntimeError("ffprobe introuvable dans le PATH")
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        log(f"ERREUR ffprobe pour {audio_path}: {stderr}")
        return None

    output = (result.stdout or "").strip()
    if not output:
        log(f"ERREUR ffprobe: sortie vide pour {audio_path}")
        return None

    try:
        return int(round(float(output)))
    except ValueError:
        log(f"ERREUR ffprobe: durée illisible '{output}' pour {audio_path}")
        return None


def fix_meta_file(meta_path: Path) -> tuple[int, int]:
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    episodes = meta.get("episodes", [])
    if not isinstance(episodes, list):
        return 0, 0

    processed = 0
    updated = 0

    for episode in episodes:
        if not isinstance(episode, dict):
            continue

        if episode.get("duration", "__missing__") is not None:
            continue

        audio_path = resolve_audio_path(episode.get("local_audio"))
        if audio_path is None:
            continue

        processed += 1
        duration = probe_duration_seconds(audio_path)
        episode_id = episode.get("id", "<sans-id>")

        if duration is None:
            log(f"[KO] {meta_path}: épisode {episode_id}, durée non calculée")
            continue

        episode["duration"] = duration
        updated += 1
        log(f"[OK] {meta_path}: épisode {episode_id}, duration={duration}s")

    if updated > 0:
        atomic_write_json(meta_path, meta)
        log(f"meta.json mis à jour atomiquement: {meta_path}")

    return processed, updated


def regenerate_data_json() -> None:
    sys.path.insert(0, str(RSS_INGEST_DIR))

    from models import Episode, PodcastMeta  # type: ignore
    from writer import update_data_json  # type: ignore

    all_meta = []
    for meta_path in sorted(PODCASTS_DIR.glob("*/meta.json")):
        with open(meta_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        episodes = [Episode(**ep) for ep in raw.get("episodes", [])]
        meta = PodcastMeta(
            id=raw.get("id"),
            label=raw.get("label"),
            language=raw.get("language"),
            cover_image=raw.get("cover_image"),
            episodes=episodes,
        )
        all_meta.append(meta)

    update_data_json(all_meta)
    log("Régénération data.json terminée via writer.update_data_json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Calcule la durée des épisodes (duration == null) depuis local_audio "
            "et met à jour meta.json de façon atomique."
        )
    )
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Ne pas relancer writer.update_data_json à la fin.",
    )
    args = parser.parse_args()

    meta_files = sorted(PODCASTS_DIR.glob("*/meta.json"))
    if not meta_files:
        log(f"Aucun meta.json trouvé dans {PODCASTS_DIR}")
        return 1

    total_processed = 0
    total_updated = 0

    for meta_file in meta_files:
        processed, updated = fix_meta_file(meta_file)
        total_processed += processed
        total_updated += updated

    log(
        "Résumé: "
        f"épisodes candidats={total_processed}, durées mises à jour={total_updated}"
    )

    if not args.skip_rebuild:
        regenerate_data_json()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as err:
        log(f"ERREUR: {err}")
        raise SystemExit(2)

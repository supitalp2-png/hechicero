#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any


SEVERITY_ORDER = {"OK": 0, "WARN": 1, "ERR": 2}
M4A_BRANDS = {b"M4A ", b"M4B ", b"isom", b"mp41", b"mp42", b"qt  "}


def resolve_project_root() -> Path:
    preferred = Path("/home/thomas/hechicero")
    if preferred.exists():
        return preferred
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = resolve_project_root()
PODCASTS_DIR = PROJECT_ROOT / "podcasts"
DATA_JSON_PATH = PROJECT_ROOT / "web" / "lecteur" / "data.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_any_path(raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    raw = raw_path.strip()
    direct = Path(raw)
    candidates: list[Path] = [direct]

    if not direct.is_absolute():
        candidates.append(PROJECT_ROOT / direct)

    if raw.startswith("/home/thomas/hechicero/"):
        rel = PurePosixPath(raw).relative_to("/home/thomas/hechicero")
        candidates.append(PROJECT_ROOT.joinpath(*rel.parts))

    if raw.startswith("/"):
        rel_from_root = PurePosixPath(raw.lstrip("/"))
        candidates.append(PROJECT_ROOT.joinpath(*rel_from_root.parts))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    return candidates[-1] if candidates else None


def path_identity(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        normalized = path.resolve(strict=False)
    except OSError:
        normalized = path

    try:
        return normalized.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return normalized.as_posix()


def detect_m4a_disguised_as_mp3(path: Path) -> bool:
    if path.suffix.lower() != ".mp3" or not path.is_file():
        return False

    try:
        with path.open("rb") as handle:
            header = handle.read(32)
    except OSError:
        return False

    if len(header) < 12:
        return False
    if header[4:8] != b"ftyp":
        return False
    return header[8:12] in M4A_BRANDS


def format_issue(level: str, podcast_id: str, label: str, message: str) -> str:
    return f"[{level}] {podcast_id} - {label}: {message}"


def collect_file_issues(podcast_id: str, label: str, role: str, path: Path | None, issues: list[tuple[str, str]]) -> None:
    if path is None:
        issues.append(("ERR", f"{role} manquant dans les métadonnées"))
        return
    if not path.exists():
        issues.append(("ERR", f"{role} introuvable: {path}"))
        return
    if not path.is_file():
        issues.append(("ERR", f"{role} invalide (pas un fichier): {path}"))
        return
    if path.stat().st_size == 0:
        issues.append(("ERR", f"{role} taille 0: {path.name}"))
        return
    if role == "audio" and detect_m4a_disguised_as_mp3(path):
        issues.append(("WARN", f"audio M4A deguise en .mp3: {path.name}"))


def check_podcast(
    podcast_id: str,
    meta: dict[str, Any] | None,
    data_entry: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    issues: list[tuple[str, str]] = []
    label = podcast_id

    if meta is None:
        issues.append(("ERR", "meta.json absent ou illisible"))
        return "ERR", [format_issue("ERR", podcast_id, label, issues[0][1])]

    label = str(meta.get("label") or podcast_id)
    if data_entry is None:
        issues.append(("ERR", "podcast absent de data.json"))

    meta_episodes = meta.get("episodes")
    if not isinstance(meta_episodes, list):
        issues.append(("ERR", "meta.json: episodes n'est pas une liste"))
        meta_episodes = []

    data_chapters = data_entry.get("chapitres", []) if isinstance(data_entry, dict) else []
    if data_entry is not None and not isinstance(data_chapters, list):
        issues.append(("ERR", "data.json: chapitres n'est pas une liste"))
        data_chapters = []

    data_by_id = {
        chapter.get("id"): chapter
        for chapter in data_chapters
        if isinstance(chapter, dict) and chapter.get("id")
    }

    referenced_audio: set[str] = set()
    referenced_images: set[str] = set()

    for episode in meta_episodes:
        if not isinstance(episode, dict):
            issues.append(("ERR", "episode meta invalide (pas un objet)"))
            continue

        episode_id = str(episode.get("id") or "<sans-id>")
        audio_path = resolve_any_path(episode.get("local_audio"))
        image_path = resolve_any_path(episode.get("local_image"))

        audio_identity = path_identity(audio_path)
        image_identity = path_identity(image_path)
        if audio_identity is not None:
            referenced_audio.add(audio_identity)
        if image_identity is not None:
            referenced_images.add(image_identity)

        episode_issues: list[tuple[str, str]] = []
        collect_file_issues(podcast_id, label, "audio", audio_path, episode_issues)
        collect_file_issues(podcast_id, label, "image", image_path, episode_issues)

        chapter = data_by_id.get(episode_id)
        if chapter is None:
            episode_issues.append(("ERR", f"episode absent de data.json: {episode_id}"))
        else:
            data_audio = resolve_any_path(chapter.get("audio"))
            data_image = resolve_any_path(chapter.get("image"))
            if data_audio is None:
                episode_issues.append(("ERR", f"audio absent dans data.json: {episode_id}"))
            elif audio_identity is not None and path_identity(data_audio) != audio_identity:
                episode_issues.append(("WARN", f"audio meta/data.json divergent pour {episode_id}"))
            elif data_audio is not None:
                collect_file_issues(podcast_id, label, "audio data.json", data_audio, episode_issues)

            if data_image is None:
                episode_issues.append(("ERR", f"image absente dans data.json: {episode_id}"))
            elif image_identity is not None and path_identity(data_image) != image_identity:
                episode_issues.append(("WARN", f"image meta/data.json divergente pour {episode_id}"))
            elif data_image is not None:
                collect_file_issues(podcast_id, label, "image data.json", data_image, episode_issues)

        for level, message in episode_issues:
            issues.append((level, f"{episode_id}: {message}"))

    if data_entry is not None and len(data_by_id) != len(meta_episodes):
        issues.append(("WARN", f"nombre d'episodes different meta/data.json ({len(meta_episodes)} vs {len(data_by_id)})"))

    cover_path = PROJECT_ROOT / "web" / "lecteur" / "images" / f"{podcast_id}.jpg"
    if not cover_path.exists():
        issues.append(("WARN", f"cover podcast manquante: {cover_path.name}"))
    elif cover_path.stat().st_size == 0:
        issues.append(("ERR", f"cover podcast taille 0: {cover_path.name}"))

    audio_dir = PODCASTS_DIR / podcast_id / "audio"
    image_dir = PODCASTS_DIR / podcast_id / "images"
    if audio_dir.exists():
        for orphan in sorted(audio_dir.iterdir()):
            if orphan.is_file() and path_identity(orphan) not in referenced_audio:
                issues.append(("WARN", f"audio orphelin: {orphan.name}"))
    if image_dir.exists():
        for orphan in sorted(image_dir.iterdir()):
            if orphan.is_file() and path_identity(orphan) not in referenced_images:
                issues.append(("WARN", f"image orpheline: {orphan.name}"))

    level = "OK"
    if issues:
        level = max(issues, key=lambda item: SEVERITY_ORDER[item[0]])[0]

    lines = [format_issue(level, podcast_id, label, "aucun probleme detecte")] if not issues else [
        format_issue(issue_level, podcast_id, label, message) for issue_level, message in issues
    ]
    return level, lines


def load_meta_by_podcast(podcast_filter: str | None) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for meta_path in sorted(PODCASTS_DIR.glob("*/meta.json")):
        podcast_id = meta_path.parent.name
        if podcast_filter and podcast_id != podcast_filter:
            continue
        try:
            result[podcast_id] = load_json(meta_path)
        except Exception:
            result[podcast_id] = None
    return result


def load_data_by_podcast(podcast_filter: str | None) -> dict[str, dict[str, Any]]:
    if not DATA_JSON_PATH.exists():
        return {}
    raw = load_json(DATA_JSON_PATH)
    podcasts = raw.get("podcasts", []) if isinstance(raw, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for podcast in podcasts:
        if not isinstance(podcast, dict):
            continue
        podcast_id = podcast.get("id")
        if not podcast_id:
            continue
        if podcast_filter and podcast_id != podcast_filter:
            continue
        result[str(podcast_id)] = podcast
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifie l'integrite des fichiers audio/images et la coherence de data.json."
    )
    parser.add_argument("--podcast", help="Verifier uniquement un podcast donne")
    args = parser.parse_args()

    meta_by_podcast = load_meta_by_podcast(args.podcast)
    data_by_podcast = load_data_by_podcast(args.podcast)

    podcast_ids = sorted(set(meta_by_podcast) | set(data_by_podcast))
    if not podcast_ids:
        print("[ERR] global - integrity: aucun podcast trouve")
        return 1

    worst_level = "OK"
    total_ok = 0
    total_warn = 0
    total_err = 0

    for podcast_id in podcast_ids:
        level, lines = check_podcast(
            podcast_id,
            meta_by_podcast.get(podcast_id),
            data_by_podcast.get(podcast_id),
        )
        if SEVERITY_ORDER[level] > SEVERITY_ORDER[worst_level]:
            worst_level = level
        for line in lines:
            print(line)
        total_ok += sum(1 for line in lines if line.startswith("[OK]"))
        total_warn += sum(1 for line in lines if line.startswith("[WARN]"))
        total_err += sum(1 for line in lines if line.startswith("[ERR]"))

    print(
        f"[OK] global - integrity: resume ok={total_ok} warn={total_warn} err={total_err} podcasts={len(podcast_ids)}"
    )
    return 2 if worst_level == "ERR" else 1 if worst_level == "WARN" else 0


if __name__ == "__main__":
    raise SystemExit(main())
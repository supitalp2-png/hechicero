import json
import os
import sys
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from parser import parse_rss
from downloader import download_episode
from writer import write_meta, update_data_json
from models import PodcastConfig, PodcastMeta
from utils import log
import progress

CONFIG_PATH = Path("/home/thomas/hechicero/data/podcasts.json")

def load_config(podcast_id=None):
    with open(CONFIG_PATH) as f:
        raw = json.load(f)
    configs = [PodcastConfig(**p) for p in raw["podcasts"] if p["enabled"]]
    if podcast_id:
        configs = [cfg for cfg in configs if cfg.id == podcast_id]
    return configs

def load_all_configs():
    with open(CONFIG_PATH) as f:
        raw = json.load(f)
    return [PodcastConfig(**p) for p in raw["podcasts"] if p["enabled"]]

def build_all_meta_from_disk(configs_all, freshly_processed):
    """Reconstruit la liste complète des PodcastMeta en lisant les meta.json existants
    pour les podcasts non traités dans cette session."""
    from models import Episode
    processed_ids = {m.id for m in freshly_processed}
    all_meta = list(freshly_processed)

    for cfg in configs_all:
        if cfg.id in processed_ids:
            continue
        meta_path = Path(f"/home/thomas/hechicero/podcasts/{cfg.id}/meta.json")
        if not meta_path.exists():
            continue
        try:
            with open(meta_path) as f:
                raw = json.load(f)
            episodes = [Episode(**e) for e in raw.get("episodes", [])]
            all_meta.append(PodcastMeta(
                id=raw["id"],
                label=raw["label"],
                language=raw["language"],
                cover_image=None,
                episodes=episodes,
            ))
        except Exception as e:
            log(f"WARNING: impossible de charger {meta_path}: {e}")

    return all_meta

def ingest(podcast_id=None):
    log("=== Démarrage synchronisation ===")
    configs = load_config(podcast_id)
    if podcast_id and not configs:
        raise ValueError(f"Podcast introuvable ou désactivé: {podcast_id}")

    progress.start(len(configs))
    all_meta = []

    for cfg in configs:
        log(f"Podcast : {cfg.label} ({cfg.id})")
        try:
            if cfg.source_type == "html_radionacional":
                from scraper_radionacional import scrape_radionacional
                episodes = scrape_radionacional(cfg)
            else:
                episodes = parse_rss(cfg)
            # parse_rss() retourne desormais les episodes tries du plus ancien
            # au plus recent (cf. TICKET-103bis) : on garde donc les cfg.max_episodes
            # les PLUS RECENTS en tronquant par la fin, pas par le debut.
            episodes = episodes[-cfg.max_episodes:] if cfg.max_episodes else episodes
            progress.start_podcast(cfg.id, cfg.label, len(episodes))

            downloaded = []
            for ep in episodes:
                try:
                    result = download_episode(cfg.id, ep)
                    downloaded.append(result)
                    # Épisode en erreur si pas d'audio après tentative
                    if ep.audio_url and not result.local_audio:
                        progress.episode_done(error=f"{cfg.id}/{ep.id} : téléchargement audio échoué")
                    else:
                        progress.episode_done()
                except Exception as e:
                    downloaded.append(ep)
                    progress.episode_done(error=f"{cfg.id}/{ep.id} : {str(e)[:120]}")

            # Télécharger la cover dans web/lecteur/images/ (accessible Apache)
            cover_local = None
            if episodes and episodes[0].image_url:
                from downloader import download_file
                cover_url = episodes[0].image_url
                cover_path = Path(f"/home/thomas/hechicero/web/lecteur/images/{cfg.id}.jpg")
                result = download_file(cover_url, cover_path)
                if result:
                    cover_local = str(result)

            meta = PodcastMeta(
                id=cfg.id,
                label=cfg.label,
                language=cfg.language,
                cover_image=cover_local,
                episodes=downloaded
            )
            write_meta(cfg.id, meta)
            all_meta.append(meta)
        except Exception as e:
            # Un podcast en échec (ex: permission refusée sur son meta.json,
            # cf. bug 2026-07-09 constaté depuis l'admin web) ne doit pas
            # interrompre la synchronisation des autres podcasts. On le
            # signale dans les erreurs de progression et on continue — la
            # reconstruction depuis le disque juste en dessous rattrapera ce
            # podcast avec son dernier meta.json valide (pas de disparition
            # de data.json).
            log(f"ERREUR podcast {cfg.id} : {e}")
            progress.episode_done(error=f"{cfg.id} : échec synchronisation — {str(e)[:150]}")
        finally:
            progress.podcast_done()

    # Reconstruire data.json avec TOUS les podcasts connus (pas seulement ceux
    # traites avec succes dans cette session) : couvre le mode --podcast ET
    # tout podcast qui aurait échoué ci-dessus (son dernier meta.json valide
    # sur disque est repris tel quel plutôt que de disparaître de data.json).
    all_meta = build_all_meta_from_disk(load_all_configs(), all_meta)

    update_data_json(all_meta)
    progress.finish()
    log("=== Synchronisation terminée ===")


def parse_args():
    parser = argparse.ArgumentParser(description="Synchronisation des podcasts")
    parser.add_argument("--podcast", help="ID du podcast a synchroniser", default=None)
    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_args()
        ingest(args.podcast)
    except Exception as e:
        log(f"ERREUR FATALE : {e}")
        progress.fatal_error(str(e)[:300])

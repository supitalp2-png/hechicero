#!/bin/bash
# Hook git post-commit — Hechicero (a copier vers .git/hooks/post-commit)
#
# Synchronise private/ (jamais suivi par git, jamais sur GitHub) vers un
# dossier dédié sur le NAS, en tâche de fond, à chaque commit. N'échoue
# jamais bruyamment : si le NAS est injoignable ou que sudo n'est pas encore
# configuré (setup pas fait), le commit se termine normalement quand même.
#
# Installation (une seule fois, voir docs/85-SAUVEGARDE_RESTAURATION.md §5) :
#   cp scripts/git_hooks_post_commit.sh .git/hooks/post-commit
#   chmod +x .git/hooks/post-commit

cd "$(git rev-parse --show-toplevel)" 2>/dev/null || exit 0

nohup sudo -n python3 scripts/backup_manager.py sync_private \
    >> data/private_sync.log 2>&1 &
disown 2>/dev/null

exit 0

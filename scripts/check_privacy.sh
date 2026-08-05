#!/bin/bash
# check_privacy.sh — Aucun prénom réel dans les fichiers versionnés (zone Z10)
#
# Le dépôt est public. Un prénom qui part dans un commit reste dans l'historique
# git : ça ne se rattrape pas, même en le supprimant ensuite. Ce script est le
# filet, à passer AVANT chaque commit.
#
# Les prénoms cherchés ne peuvent évidemment PAS être écrits ici — ce fichier est
# lui-même versionné et public. Ils vivent dans :
#
#     private/forbidden_names.txt        ← exclu du dépôt par .gitignore
#
# Format : une expression régulière par ligne. Lignes vides et lignes commençant
# par # ignorées. Utiliser des limites de mot :
#
#     \bprenom\b
#
# Sans les \b, on récolte des faux positifs : un prénom de 4 lettres se retrouve
# à cheval sur deux mots dans les identifiants d'épisodes espagnols de data.json.
#
# Usage :  ./scripts/check_privacy.sh
# Sortie :  0 = propre  ·  1 = fuite détectée  ·  2 = impossible de vérifier
#
# Effets de bord : aucun. Lecture seule.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LISTE="$ROOT/private/forbidden_names.txt"

cd "$ROOT" || { echo "❌ dépôt introuvable"; exit 2; }

# ── 1. La liste existe-t-elle ? ─────────────────────────────────────────────
if [ ! -f "$LISTE" ]; then
    echo "⚠️  private/forbidden_names.txt absent — impossible de vérifier."
    echo "    Créer le fichier avec un motif par ligne, ex. : \\bprenom\\b"
    exit 2
fi

# ── 2. La liste est-elle bien exclue du dépôt ? ─────────────────────────────
# Garde-fou essentiel : si private/ cessait d'être ignoré, ce serait la liste
# elle-même qui fuiterait — soit exactement ce qu'on cherche à empêcher.
if git check-ignore -q "$LISTE" 2>/dev/null; then
    :
elif git ls-files --error-unmatch "private/forbidden_names.txt" >/dev/null 2>&1; then
    echo "❌ GRAVE : private/forbidden_names.txt est SUIVI PAR GIT."
    echo "    La liste des prénoms interdits est en passe d'être publiée."
    echo "    → git rm --cached private/forbidden_names.txt && vérifier .gitignore"
    exit 1
else
    echo "⚠️  impossible de confirmer que private/ est ignoré — vérifier .gitignore"
fi

motifs=$(grep -vE '^[[:space:]]*(#|$)' "$LISTE" | paste -sd'|' -)
if [ -z "$motifs" ]; then
    echo "⚠️  private/forbidden_names.txt est vide — rien à chercher."
    exit 2
fi

# ── 3. Balayage des fichiers suivis ─────────────────────────────────────────
# `git ls-files` plutôt qu'un `find` : on ne s'intéresse qu'à ce qui part
# réellement sur GitHub. Les fichiers de travail non suivis n'ont pas d'importance,
# et private/ n'en fait pas partie par construction.
fichiers=$(git ls-files 2>/dev/null)
if [ -z "$fichiers" ]; then
    echo "⚠️  git ls-files n'a rien renvoyé (dépôt cassé ?) — vérification impossible."
    exit 2
fi

# -I saute les binaires (images, mp3), -i insensible à la casse.
fuites=$(printf '%s\n' "$fichiers" | while IFS= read -r f; do
    [ -f "$f" ] || continue
    grep -InE "$motifs" -- "$f" 2>/dev/null | sed "s|^|$f:|"
done)

# ── 4. Verdict ──────────────────────────────────────────────────────────────
n_motifs=$(grep -cvE '^[[:space:]]*(#|$)' "$LISTE")
n_fichiers=$(printf '%s\n' "$fichiers" | wc -l)

if [ -n "$fuites" ]; then
    echo "❌ FUITE — prénom réel trouvé dans des fichiers suivis par git :"
    echo
    printf '%s\n' "$fuites" | sed 's/^/    /'
    echo
    echo "    NE PAS COMMITTER. Remplacer par « le petit », « papa », « la maman »,"
    echo "    ou déplacer le contenu concerné dans private/."
    exit 1
fi

echo "✅ aucun prénom réel dans les $n_fichiers fichiers suivis ($n_motifs motif(s) cherché(s))"
exit 0

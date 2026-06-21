{
  echo "=== DUMP DOCS — Hechicero ===";
  echo "Date : $(date '+%Y-%m-%d %H:%M:%S')";
  echo "";
  find docs -type f -name "*.md" -print0 | sort -z | while IFS= read -r -d '' f; do
    echo "=== FILE: $f ===";
    cat "$f";
    echo "";
  done
} > docs_dump.txt
#!/bin/zsh
# Publish this repository to GitHub as a rewritten copy: the working repository is never modified.
# A fresh clone is filtered with git-filter-repo (drop every .blend, drop every blob over 2 MB, rewrite the author
# email to the GitHub noreply address, scrub the personal email from file contents) and pushed. Re-runnable: filter-repo
# is deterministic, so unchanged history keeps its rewritten ids and a later run pushes only the new commits.
#   scripts/publish_github.sh [remote-url]        default git@github.com:dkhh10/palace-of-fine-arts-3d.git
# Requires: git-filter-repo on PATH, gh logged in (for the first run's repo creation, done by hand, see README).
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${1:-git@github.com:dkhh10/palace-of-fine-arts-3d.git}"
WORK="${PFA_PUBLISH_DIR:-$HOME/.cache/pfa_publish}"
rm -rf "$WORK"; mkdir -p "$WORK"
git clone --quiet --no-local --bare "$SRC" "$WORK/src.git"
cd "$WORK/src.git"
# drop refs that are not branches or tags (remote-tracking, notes) so filter-repo sees only what we publish
git for-each-ref --format='%(refname)' refs/ | grep -v -E '^refs/(heads|tags)/' | xargs -r -n1 git update-ref -d
cat > "$WORK/mailmap" <<'EOF'
dk <dkhh10@users.noreply.github.com> <dkhh10@users.noreply.github.com>
EOF
cat > "$WORK/replace.txt" <<'EOF'
dkhh10@users.noreply.github.com==>dkhh10@users.noreply.github.com
EOF
git filter-repo --force \
  --path-glob '*.blend' --invert-paths \
  --strip-blobs-bigger-than 2M \
  --mailmap "$WORK/mailmap" \
  --replace-text "$WORK/replace.txt"
git remote add origin "$REMOTE"
git push --force --all origin
git push --force --tags origin
echo "pushed $(git for-each-ref refs/heads | wc -l | tr -d ' ') branches to $REMOTE; pack $(git count-objects -vH | awk '/size-pack/{print $2, $3}')"

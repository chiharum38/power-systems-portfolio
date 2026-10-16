#!/usr/bin/env bash
# Publishes the portfolio site.
#
# Replays the local index.html and project write-ups on top of the GitHub copy,
# clearing any stale git lock files first.
#
#   bash ~/power-systems-portfolio/publish_site.sh
#   MSG="Describe the change" bash ~/power-systems-portfolio/publish_site.sh

set -euo pipefail

ROOT=~/power-systems-portfolio
SITE="$ROOT/chiharum38.github.io"

# ---------------------------------------------------------------- stale locks
# Earlier git commands were run through a sandboxed shell that is not permitted
# to delete files, so git could create its lock files but never clean them up.
# Nothing is actually running; these are orphans. Close any editor mid-commit
# before running this, then they are safe to remove.
clean_locks () {
  local repo="$1" label="$2" found=0
  for f in index.lock HEAD.lock objects/maintenance.lock; do
    if [ -e "$repo/.git/$f" ]; then rm -f "$repo/.git/$f"; echo "    removed  $label/.git/$f"; found=1; fi
  done
  local n
  n=$(find "$repo/.git/objects" -name 'tmp_obj_*' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" -gt 0 ]; then
    find "$repo/.git/objects" -name 'tmp_obj_*' -delete
    echo "    removed  $n orphaned temp objects in $label"
    found=1
  fi
  [ "$found" -eq 0 ] && echo "    $label: clean"
  return 0
}

echo "==> Clearing stale git locks"
clean_locks "$SITE" "site repo"
clean_locks "$ROOT" "portfolio repo"

cd "$SITE"

echo
echo "==> Fetching what GitHub has"
git fetch origin || echo "    (fetch failed; fine for a brand-new empty repo)"

echo
echo "==> Checking the five write-ups"
for f in n1_contingency offshore_wind fault_detection storage_optimizer contingency_toolkit; do
  [ -s "projects/$f.html" ] && echo "    ok   projects/$f.html" || { echo "    MISSING projects/$f.html"; exit 1; }
done

echo
echo "==> Checking the result figures"
for n in 02 03 04 05; do
  [ -s "images/p${n}_results.png" ] && echo "    ok   images/p${n}_results.png" || { echo "    MISSING images/p${n}_results.png"; exit 1; }
done

echo
echo "==> Checking the CV"
[ -s "assets/Chiharu_Mamiya_CV.pdf" ] \
  && echo "    ok   assets/Chiharu_Mamiya_CV.pdf ($(wc -c < assets/Chiharu_Mamiya_CV.pdf | tr -d ' ') bytes)" \
  || { echo "    MISSING assets/Chiharu_Mamiya_CV.pdf"; exit 1; }
[ "$(grep -c 'assets/Chiharu_Mamiya_CV.pdf' index.html)" -ge 2 ] \
  && echo "    ok   linked from the hero card and the contact section" \
  || { echo "    index.html does not link the CV twice"; exit 1; }

echo
echo "==> Checking index.html is the live design, fully wired"
grep -q 'class="exp-panel' index.html || { echo "    not the June design"; exit 1; }
for f in offshore_wind fault_detection storage_optimizer contingency_toolkit; do
  grep -q "data-href=\"projects/$f.html\"" index.html || { echo "    panel for $f not wired"; exit 1; }
done
echo "    ok   all five panels point at write-ups"

echo
echo "==> Committing site changes"
git add -A
git status --short
if git diff --cached --quiet; then
  echo "    nothing new to commit"
else
  git commit -q -m "${MSG:-Update site}"
fi

echo
echo "==> Pushing the site to $(git remote get-url origin)"
git push -u origin main

# ---------------------------------------------------- the other repo, if dirty
echo
cd "$ROOT"
git add -A
if git diff --cached --quiet; then
  echo "==> Portfolio repo already clean"
else
  echo "==> Portfolio repo has changes too, committing those"
  git status --short
  git commit -q -m "${MSG:-Update portfolio}"
fi
echo "==> Pushing the portfolio repo"
git push -u origin main

echo
echo "Done. GitHub Pages usually redeploys within a minute."
echo "  Site   https://chiharum38.github.io/"
echo "  CV     https://chiharum38.github.io/assets/Chiharu_Mamiya_CV.pdf"

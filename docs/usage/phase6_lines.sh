#!/bin/zsh
# Lines added/removed on all branches in the Phase 6 days, by area of the repo (what the output tokens became).
# Usage: docs/usage/phase6_lines.sh [since] [until]   (defaults 2026-09-15 .. 2026-09-18)
cd "$(dirname "$0")/../.."
git log --all --no-merges --since="${1:-2026-09-15}T00:00" --until="${2:-2026-09-18}T23:59:59" --numstat --format='' | awk -F'\t' '$1!="-"{ p=$3; c="other";
 if(p~/^web\/src\//)c="web/src (viewer JavaScript)"; else if(p~/^web\/(tools|test)\//)c="web/tools+test";
 else if(p~/^export\/(bake|gate[0-9]_(bake|lm|set|encode|imp|env|common)|bake_queue|lut|light)/)c="export/ bake scripts"; else if(p~/^export\//)c="export/ export+pack scripts";
 else if(p~/^scripts\/qa_/)c="scripts/qa_* (critic probes)"; else if(p~/^docs\/qa_round/)c="docs/qa_round (critic reports)"; else if(p~/^docs\/reviews/)c="docs/reviews";
 else if(p~/^docs\/briefs/)c="docs/briefs (lead)"; else if(p~/^docs\/(status|decisions|delivery|tech_notes)/)c="docs/status+decisions+delivery+tech_notes (lead)"; else if(p~/^docs\//)c="docs other";
 else if(p~/^renders\//)c="renders (json sidecars)"; else if(p~/^scripts\//)c="scripts other"; a[c]+=$1; d[c]+=$2} END{for(k in a) printf "%8d %7d  %s\n", a[k], d[k], k}' | sort -rn

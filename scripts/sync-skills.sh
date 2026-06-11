#!/usr/bin/env bash
# トップレベルの <skill>/ (単一ソース) から .claude/skills/ を生成する。
# agents/ (Codex 固有) はコピーしない。
# 使い方:
#   ./scripts/sync-skills.sh          # 同期を実行
#   ./scripts/sync-skills.sh --check  # 差分の有無だけ確認 (CI 向け、差分があれば exit 1)
set -euo pipefail

cd "$(dirname "$0")/.."

MODE="${1:-sync}"
DEST=".claude/skills"

# SKILL.md を持つトップレベルディレクトリをスキルとみなす
skills=()
for dir in */; do
  name="${dir%/}"
  [[ -f "$name/SKILL.md" ]] && skills+=("$name")
done

if [[ ${#skills[@]} -eq 0 ]]; then
  echo "スキルが見つかりません" >&2
  exit 1
fi

if [[ "$MODE" == "--check" ]]; then
  status=0
  for name in "${skills[@]}"; do
    if ! diff -r -x agents "$name" "$DEST/$name" >/dev/null 2>&1; then
      echo "drift: $name"
      status=1
    fi
  done
  # ソースに存在しない生成物の検出
  for dir in "$DEST"/*/; do
    name="$(basename "$dir")"
    [[ -f "$name/SKILL.md" ]] || { echo "orphan: $DEST/$name"; status=1; }
  done
  [[ $status -eq 0 ]] && echo "OK: drift なし"
  exit $status
fi

mkdir -p "$DEST"

# ソースに存在しない生成物を削除
for dir in "$DEST"/*/; do
  [[ -d "$dir" ]] || continue
  name="$(basename "$dir")"
  if [[ ! -f "$name/SKILL.md" ]]; then
    rm -rf "$dir"
    echo "removed: $DEST/$name"
  fi
done

# 同期 (agents/ を除外して丸ごと作り直す)
for name in "${skills[@]}"; do
  rm -rf "${DEST:?}/$name"
  mkdir -p "$DEST/$name"
  (cd "$name" && find . -type f -not -path './agents/*' -exec sh -c '
    for f; do
      mkdir -p "$0/$(dirname "$f")"
      cp "$f" "$0/$f"
    done
  ' "../$DEST/$name" {} +)
  echo "synced: $name"
done

echo "完了: ${#skills[@]} スキルを $DEST へ同期しました"

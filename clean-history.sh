#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="multi-agent-ecommerce-optimizer"
BACKUP_DIR="$HOME/repo-backups/${REPO_NAME}-final-state-$(date +%Y%m%d-%H%M%S)"

MAIN_COMMIT_MSG="feat(frontend): update logo text mark and hero alignment"
DEV_COMMIT_MSG="chore(dev): restore latest project state"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Hata: Bu klasör bir git reposu değil."
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "Repo: $REPO_ROOT"
echo "Backup: $BACKUP_DIR"
echo

read -r -p "Claude commitleri historyden silinsin, dosyalar korunsun mu? yes/no: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "İptal edildi."
  exit 0
fi

echo
echo "1) Mevcut dosya hali git dışına yedekleniyor..."

mkdir -p "$BACKUP_DIR"

rsync -a \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  ./ "$BACKUP_DIR/"

echo "Yedek alındı: $BACKUP_DIR"

echo
echo "2) Remote güncelleniyor..."
git fetch origin

echo
echo "3) main temizleniyor..."
git checkout main
git reset --hard origin/main~1

rsync -a --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  "$BACKUP_DIR/" ./

git add -A

if git diff --cached --quiet; then
  echo "main için değişiklik yok, commit atlanıyor."
else
  git commit -m "$MAIN_COMMIT_MSG"
fi

git push --force-with-lease origin main

echo
echo "4) dev temizleniyor..."
git checkout dev
git reset --hard origin/dev~2

rsync -a --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  "$BACKUP_DIR/" ./

git add -A

if git diff --cached --quiet; then
  echo "dev için değişiklik yok, commit atlanıyor."
else
  git commit -m "$DEV_COMMIT_MSG"
fi

git push --force-with-lease origin dev

echo
echo "5) Kontrol:"
git fetch origin

echo
echo "origin/main son 10 commit:"
git log --oneline origin/main -10

echo
echo "origin/dev son 10 commit:"
git log --oneline origin/dev -10

echo
echo "Bitti."
echo "Şu commitler artık görünmemeli:"
echo "391f297"
echo "860847d"
echo "467cfe9"
echo
echo "Local yedek:"
echo "$BACKUP_DIR"

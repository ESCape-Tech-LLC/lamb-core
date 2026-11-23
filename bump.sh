#!/bin/bash

set -e

BUMP_PART=${1:-patch}
CHANGELOG_FILE="CHANGELOG.md"
PYPROJECT_FILE="pyproject.toml"

echo "🚀 Bumping version: $BUMP_PART"

# 1. Получить текущую версию
CURRENT_VERSION=$(grep -E '^version = ' "$PYPROJECT_FILE" | head -1 | sed 's/version = "\(.*\)"/\1/')

# 2. Рассчитать новую версию через bump-my-version
case "$BUMP_PART" in
    major)
        NEW_VERSION=$(uvx bump-my-version show-bump 2>&1 | sed -n 's/.*─ major ─ \([0-9.]*\)/\1/p')
        ;;
    minor)
        NEW_VERSION=$(uvx bump-my-version show-bump 2>&1 | sed -n 's/.*─ minor ─ \([0-9.]*\)/\1/p')
        ;;
    patch)
        NEW_VERSION=$(uvx bump-my-version show-bump 2>&1 | sed -n 's/.*─ patch ─ \([0-9.]*\)/\1/p')
        ;;
    *)
        echo "❌ Invalid bump part: $BUMP_PART"
        exit 1
        ;;
esac

if [ -z "$NEW_VERSION" ]; then
    echo "❌ Could not calculate new version"
    exit 1
fi

echo "📌 $CURRENT_VERSION → $NEW_VERSION"

# 3. Обновить CHANGELOG.md
if [ -f "$CHANGELOG_FILE" ]; then
    TODAY=$(date +%Y-%m-%d)
    
    # Заменяем Unreleased на новую версию с датой
    sed -i.bak "s/## \[Unreleased\]/## [$NEW_VERSION] - $TODAY/" "$CHANGELOG_FILE"
    rm -f "${CHANGELOG_FILE}.bak"
    
    # Добавляем новую пустую Unreleased секцию в начало (после # Changelog)
    TEMP_FILE=$(mktemp)
    {
        echo "# Changelog"
        echo ""
        echo "## [Unreleased]"
        echo ""
        echo "---"
        # Удаляем старый # Changelog из остального контента
        sed '1d' "$CHANGELOG_FILE"
    } > "$TEMP_FILE"
    mv "$TEMP_FILE" "$CHANGELOG_FILE"
    
    echo "✅ CHANGELOG.md updated"
else
    echo "⚠️  CHANGELOG.md not found, skipping"
fi

# 4. Commit изменения CHANGELOG.md
echo "📝 Committing CHANGELOG.md..."
git add "$CHANGELOG_FILE"
git commit -m "docs: prepare changelog for v$NEW_VERSION"

# 5. Bump версии (создаёт свой commit + tag)
echo "🔧 Running bump-my-version..."
uvx bump-my-version bump "$BUMP_PART"

# 6. Push
echo "📤 Pushing changes..."
git push
git push --tags

echo "✅ Done! $CURRENT_VERSION → $NEW_VERSION"
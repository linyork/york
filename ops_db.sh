#!/bin/bash
###############################################################################
# LanceDB 管理工具
# 用途：管理向量資料庫（備份、還原、重置）
###############################################################################

set -e

# 載入 .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_PATH="${YORK_KNOWLEDGE_ROOT}/lancedb"
BACKUP_DIR="${YORK_KNOWLEDGE_ROOT}/backups"

# 確保備份目錄存在
mkdir -p "$BACKUP_DIR"

function show_help {
    echo "用法: ./lancedb.sh [指令]"
    echo ""
    echo "指令:"
    echo "  backup    備份向量資料庫"
    echo "  reset     重置（刪除）向量資料庫"
    echo "  help      顯示此說明"
    echo ""
}

function backup_db {
    if [ ! -d "$DB_PATH" ]; then
        echo "❌ 資料庫不存在: $DB_PATH"
        exit 1
    fi
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/lancedb_$TIMESTAMP.tar.gz"
    
    echo "📦 正在備份資料庫..."
    tar -czf "$BACKUP_FILE" -C "$(dirname "$DB_PATH")" lancedb
    
    echo "✅ 備份完成: $BACKUP_FILE"
}

function reset_db {
    if [ ! -d "$DB_PATH" ]; then
        echo "⚠️  資料庫不錯在，無需重置"
        return
    fi
    
    echo "⚠️  警告：這將刪除所有向量資料！"
    read -p "確定要繼續嗎？ (y/N): " confirm
    
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "已取消"
        exit 0
    fi
    
    # 先自動備份
    backup_db
    
    echo "🗑️  正在刪除資料庫..."
    rm -rf "$DB_PATH"
    
    echo "✅ 資料庫已重置"
}

case "$1" in
    backup)
        backup_db
        ;;
    reset)
        reset_db
        ;;
    *)
        show_help
        ;;
esac

#!/bin/bash
# ============================================
# 竞品雷达 - 日志清理脚本
# 用途：清理 Docker 日志，释放磁盘空间
# 用法：bash scripts/cleanup.sh
# 建议：添加到宝塔计划任务，每天凌晨执行
# ============================================

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始清理..."

# 1. 限制 Docker 容器日志大小（只保留最近 100MB）
echo "清理 Docker 日志..."
docker ps -q | while read id; do
    log_path=$(docker inspect --format='{{.LogPath}}' "$id" 2>/dev/null)
    if [ -n "$log_path" ] && [ -f "$log_path" ]; then
        truncate -s 0 "$log_path"
    fi
done

# 2. 清理无用的 Docker 缓存
echo "清理 Docker 构建缓存..."
docker system prune -f --volumes 2>/dev/null || true

# 3. 清理系统日志
echo "清理系统日志..."
journalctl --vacuum-time=3d 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清理完成"

# 显示当前磁盘使用情况
df -h / | awk 'NR==2 {printf "当前磁盘: %s / %s (%s)\n", $3, $2, $5}'

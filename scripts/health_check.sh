#!/bin/bash
# ============================================
# 竞品雷达 - 服务健康检查脚本
# 用途：检查 Docker 容器状态、磁盘空间、API 健康
# 用法：bash scripts/health_check.sh
# ============================================

set -e

echo "============================================"
echo "  竞品雷达 - 服务健康检查"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# 1. Docker 容器状态
echo ""
echo "[1/4] Docker 容器状态:"
docker compose ps --services --filter "status=running" 2>/dev/null | while read service; do
    echo "  ✅ $service"
done

# 检查是否有未运行的容器
total=$(docker compose ps --services 2>/dev/null | wc -l)
running=$(docker compose ps --services --filter "status=running" 2>/dev/null | wc -l)
if [ "$total" != "$running" ]; then
    echo "  ⚠️  有 $((total - running)) 个容器未运行！"
fi

# 2. API 健康检查
echo ""
echo "[2/4] API 健康检查:"
http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$http_code" = "200" ]; then
    echo "  ✅ /health → $http_code"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
else
    echo "  ❌ /health → $http_code (异常)"
fi

# 3. 磁盘使用情况
echo ""
echo "[3/4] 磁盘使用情况:"
df -h / | awk 'NR==2 {printf "  已用: %s / %s (%s)\n", $3, $2, $5}'
if [ "$(df / | awk 'NR==2 {print $5}' | tr -d '%')" -gt 80 ]; then
    echo "  ⚠️  磁盘使用率超过 80%，建议清理！"
fi

# 4. 日志大小
echo ""
echo "[4/4] Docker 日志大小:"
docker ps --format '{{.Names}}' | while read name; do
    size=$(docker inspect --format='{{.LogPath}}' "$name" 2>/dev/null | xargs ls -lh 2>/dev/null | awk '{print $5}')
    echo "  $name: $size"
done

echo ""
echo "============================================"
echo "  检查完成"
echo "============================================"

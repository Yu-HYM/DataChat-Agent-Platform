#!/bin/bash
# 部署脚本：一键构建并启动 DataChat 容器
# 用法：bash deploy.sh

set -e

echo "=== DataChat Docker 部署 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误：未检测到 Docker，请先安装 Docker Desktop"
    exit 1
fi

# 检查 Ollama 是否在运行
if ! curl -s http://localhost:11434/ > /dev/null 2>&1; then
    echo "警告：Ollama 未启动，请先在 Windows 宿主机启动 Ollama"
fi

# 检查 MySQL 是否在运行
if ! curl -s http://localhost:9000/ > /dev/null 2>&1; then
    echo "提示：MySQL 需在 WSL2 中运行（sudo service mysql start）"
fi

echo ""
echo "=== 构建并启动容器 ==="
docker compose up -d --build

echo ""
echo "=== 等待服务就绪 ==="
sleep 10

echo ""
echo "=== 服务状态 ==="
docker compose ps

echo ""
echo "=== 部署完成 ==="
echo "前端：http://localhost:8501"
echo "API：  http://localhost:9000"
echo ""
echo "常用命令："
echo "  查看日志：docker compose logs -f"
echo "  停止服务：docker compose down"
echo "  重建镜像：docker compose build --no-cache"

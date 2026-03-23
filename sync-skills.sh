#!/bin/bash

# Auto-Prompt Skills 同步脚本
# 将核心项目的 skills 同步到桌面端项目

set -e

# 配置路径
CORE_PROJECT="/Users/gooddream/Desktop/projects/Auto-Prompt/.windsurf/skills"
DESKTOP_PROJECT="/Users/gooddream/Desktop/projects/auto-prompt-desktop/skills"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔄 同步 Auto-Prompt Skills..."
echo "================================"
echo "核心项目: $CORE_PROJECT"
echo "桌面项目: $DESKTOP_PROJECT"
echo ""

# 检查核心项目是否存在
if [ ! -d "$CORE_PROJECT" ]; then
    echo -e "${RED}✗ 错误: 核心项目 skills 目录不存在${NC}"
    echo "请检查路径: $CORE_PROJECT"
    exit 1
fi

# 确保桌面项目 skills 目录存在
mkdir -p "$DESKTOP_PROJECT"

# 执行同步
echo "正在同步文件..."
rsync -av --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.egg-info' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='*.log' \
    "$CORE_PROJECT/" \
    "$DESKTOP_PROJECT/"

echo ""
echo -e "${GREEN}✓ 同步完成${NC}"
echo ""

# 显示同步后的目录结构
echo "同步后的技能列表:"
ls -la "$DESKTOP_PROJECT"

#!/bin/bash
# 文档要素提取提示词生成器 - 启动脚本
# 用法: ./run.sh [工作目录]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${1:-$(pwd)}"

echo "工作目录: $WORK_DIR"
echo "脚本目录: $SCRIPT_DIR"
echo ""

# 检查必要文件
if [ ! -f "$WORK_DIR/factors.csv" ]; then
    echo "[错误] 未找到 factors.csv 文件"
    echo "请确保工作目录包含 factors.csv"
    exit 1
fi

# template.txt 是可选的，如果不存在会使用默认模板
if [ ! -f "$WORK_DIR/template.txt" ]; then
    echo "[提示] 未找到自定义模板，将使用默认模板"
fi

# 运行脚本
cd "$SCRIPT_DIR"
python3 generate_prompt.py "$WORK_DIR"

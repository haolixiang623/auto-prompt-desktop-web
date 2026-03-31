#!/usr/bin/env python3
"""诊断本地登录问题"""
import requests
import json

print("=== 本地登录诊断 ===\n")

# 1. 检查后端服务
print("1. 检查后端服务 (http://127.0.0.1:3000)...")
try:
    response = requests.get('http://127.0.0.1:3000/api/health', timeout=5)
    print(f"   状态: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ 后端服务正常运行")
    else:
        print(f"   ⚠️ 后端返回: {response.text}")
except Exception as e:
    print(f"   ❌ 后端服务未启动: {e}")
    print("   请先启动后端: cd pyserver && python -m uvicorn app.main:app --host 0.0.0.0 --port 3000")

# 2. 测试登录接口
print("\n2. 测试登录接口...")
try:
    response = requests.post(
        'http://127.0.0.1:3000/api/auth/login',
        json={'username': 'admin', 'password': 'admin123'},
        timeout=5
    )
    print(f"   状态: {response.status_code}")
    print(f"   响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"   ❌ 登录失败: {e}")

# 3. 检查前端代理
print("\n3. 检查前端代理配置...")
print("   vite.config.js 中代理设置: /api -> http://127.0.0.1:3000")
print("   前端地址: http://localhost:1420")
print("   API 应该通过代理访问")

print("\n=== 常见解决方案 ===")
print("1. 确保后端服务已启动:")
print("   cd pyserver && python -m uvicorn app.main:app --host 0.0.0.0 --port 3000")
print("\n2. 检查浏览器控制台错误 (F12 -> Console)")
print("\n3. 重启前端服务:")
print("   按 Ctrl+C 停止，然后 npm run dev")
print("\n4. 清除浏览器缓存:")
print("   Ctrl+Shift+R 或 Ctrl+F5")

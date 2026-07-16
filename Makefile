# 仓库追踪系统 - 本地开发与验证
.PHONY: verify build-firmware build-android test-server run-server install-server help

help:
	@echo "verify        - 运行完整本地门禁"
	@echo "build-firmware - 构建标签与网关固件（需本地 config.h）"
	@echo "build-android - 运行 Android 单元测试并构建 Debug APK"
	@echo "test-server   - 运行服务端 pytest"
	@echo "run-server    - 启动 Flask 服务（需先 install-server）"
	@echo "install-server - 安装服务端依赖（含测试）"

verify:
	bash scripts/verify.sh

build-firmware:
	pio run -e tag
	pio run -e gateway

build-android:
	cd android_app && ./gradlew --no-daemon testDebugUnitTest assembleDebug

install-server:
	cd server && python3 -m venv .venv 2>/dev/null || true && .venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt

test-server:
	cd server && (python3 -m pytest tests/ -v || .venv/bin/python -m pytest tests/ -v)

run-server:
	cd server && (python3 server.py || .venv/bin/python server.py)

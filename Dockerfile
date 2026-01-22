# 使用 Python 3.12 Slim 作為基底
FROM python:3.12-slim-bookworm

# 設定工作目錄
WORKDIR /app

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # 讓 uv 安裝到預設的 .venv 虛擬環境
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 將虛擬環境加入 PATH，這是關鍵修改
ENV PATH="/app/.venv/bin:$PATH"


# 安裝系統依賴 (git 用於某些 python 套件, build-essential 用於編譯)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 複製依賴定義檔
COPY pyproject.toml uv.lock ./
# .env 會在啟動時掛載或複製，這裡先不複製以免洩漏敏感資訊，或是由 start.sh 處理環境變數

# 安裝依賴 (不含 dev 依賴)
RUN uv sync --no-dev --frozen

# 複製原始碼
COPY src ./src

# 確保 src 目錄在 Python Path 中
ENV PYTHONPATH=/app

# 設定預設指令
CMD ["python", "-m", "src"]

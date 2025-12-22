FROM ultralytics/ultralytics:latest-cpu

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN pip install uv --no-cache-dir

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_SYSTEM_PYTHON=true

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

COPY ./uv.lock \
    ./pyproject.toml \
    ./

RUN uv venv --system-site-packages
RUN uv sync

# Копирование исходного кода
COPY *.py ./
# Копирование исходного кода
COPY etalon /app/etalon

# Создание директории для данных
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "80"]

FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends cmake g++ && rm -rf /var/lib/apt/lists/*
COPY engine-cpp /src
RUN mkdir /build && g++ -std=c++17 -O3 /src/main.cpp -o /build/novaquant_engine && g++ -std=c++17 -O3 -fPIC -shared /src/backtest.cpp -o /build/libnovaquant_backtest.so
FROM python:3.12-slim
WORKDIR /app
COPY requirements-runtime.txt requirements-telemetry.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt -r requirements-telemetry.txt
COPY backend backend
COPY engine-cpp engine-cpp
COPY tests tests
COPY scripts scripts
COPY --from=build /build/novaquant_engine /app/build-engine/novaquant_engine
COPY --from=build /build/libnovaquant_backtest.so /app/build-engine/libnovaquant_backtest.so
RUN useradd --create-home novaquant && mkdir artifacts && chown novaquant:novaquant artifacts
USER novaquant
CMD ["uvicorn","backend.api.app:app","--host","0.0.0.0","--port","8001"]

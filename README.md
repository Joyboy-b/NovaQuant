# NovaQuant Trading Platform

## Quick Start (Windows)
1. python -m venv venv
2. .\venv\Scripts\Activate
3. pip install -r backend\requirements.txt
4. cd frontend && npm install && cd ..
5. cd build-engine && cmake -S . -B . -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build . --parallel && cd ..
6. In one terminal: cd backend\api && uvicorn app:app --reload
7. In another: cd frontend && npm run dev

Dashboard → http://localhost:5173
API Docs   → http://localhost:8000/docs

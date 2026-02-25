"""
run.py - Точка входа приложения Project 5 «Биотех225».
Запуск: python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

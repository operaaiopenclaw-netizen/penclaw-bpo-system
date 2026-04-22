FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    pyjwt \
    pydantic \
    python-multipart

# Copiar código
COPY main.py .

# Expor porta
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

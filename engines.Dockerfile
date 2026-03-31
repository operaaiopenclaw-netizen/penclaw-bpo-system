# ===============================================
# Python Engines Service
# ===============================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python engines
COPY agent_runtime_core.py ./
COPY kitchen_control_layer.py ./
COPY fixed_cost_engine.py ./
COPY dre_engine.py ./
COPY kitchen_data/ ./kitchen_data/
COPY output/ ./output/

# Run the runtime core
CMD ["python3", "agent_runtime_core.py"]

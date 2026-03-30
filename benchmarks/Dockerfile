FROM python:3.12-slim

WORKDIR /app

# Install benchmark dependencies
COPY benchmarks/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the library itself from source
COPY src/ /app/src/
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
RUN pip install --no-cache-dir -e .

# Copy benchmark code
COPY benchmarks/models.py /app/models.py
COPY benchmarks/benchmark.py /app/benchmark.py
COPY benchmarks/plot.py /app/plot.py

CMD ["python", "benchmark.py"]

FROM python:3.11-slim

# System libraries required by opencv-python-headless and mysql-connector-python
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        default-libmysqlclient-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Face images are written here at runtime — mount a volume in production so
# they survive container restarts/redeploys.
RUN mkdir -p dataset

EXPOSE 5000

# gunicorn is a production-grade WSGI server; the Flask development server
# used by `python app.py` is not designed for production traffic.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]

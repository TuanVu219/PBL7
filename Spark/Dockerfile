FROM apache/spark:3.5.1
USER root
RUN apt-get update && \
    apt-get install -y python3-pip && \
    pip3 install --no-cache-dir pandas numpy feedparser beautifulsoup4 requests curl_cffi SQLAlchemy psycopg2-binary
WORKDIR /app
USER 185
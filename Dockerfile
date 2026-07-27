# Kannada / Tulu literacy tutor — production image.
#
#   docker build -t kannada-tutor .
#   docker run -p 8501:8501 -e TUTOR_TEACHER_PIN=<your-pin> \
#              -v tutor-data:/app/data kannada-tutor
#
# Then open http://localhost:8501.
#
# NOTE ON THE MICROPHONE: browsers only expose getUserMedia on a SECURE origin.
# http://localhost is treated as secure, so a local run works. Any other host
# MUST be served over HTTPS or the mic button will not appear — put this behind a
# reverse proxy with TLS (Caddy/nginx + Let's Encrypt, both free).

FROM python:3.11-slim

# ffmpeg/libav: faster-whisper decodes the browser's recording through PyAV, and
# libgomp is required by ctranslate2's CPU backend. Without these the app boots
# fine and then fails the moment a child speaks — which is the worst place to
# find out.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so a code change doesn't reinstall the world.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the speech model into the image so the container never needs the network
# at runtime — a classroom deploy can be fully offline. This adds ~250 MB and a
# few minutes to the build; it is the difference between "works in the school"
# and "works if the school has wifi".
RUN python -m scripts.convert_model || \
    echo "WARNING: model conversion failed at build time; the app will download it on first use."

# Streamlit's own health endpoint, so an orchestrator can tell a booting
# container (the model takes a few seconds to load) from a broken one.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health').read()"

EXPOSE 8501

# headless: no attempt to open a browser inside the container.
# address 0.0.0.0: otherwise Streamlit binds to loopback and the port publish
# does nothing, which looks exactly like a crashed container.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]

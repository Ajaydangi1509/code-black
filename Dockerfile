FROM python:3.11-slim

# OS dependencies for Playwright
RUN apt-get update && \
    apt-get install -y wget gnupg curl libnss3 libatk-bridge2.0-0 libxkbcommon0 libgtk-3-0 libasound2 && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Playwright browser install
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps

# App code copy
WORKDIR /app
COPY . .

# Port expose (Render $PORT environment variable use karta hai)
EXPOSE 10000

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
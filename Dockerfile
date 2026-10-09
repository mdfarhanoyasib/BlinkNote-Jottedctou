FROM python:3.11-slim

# FFmpeg ইনস্টল করা
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ডিপেন্ডেন্সি ইনস্টল
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# কোড কপি
COPY . .

# Render-এর ডিফল্ট পোর্ট
ENV PORT=7860
EXPOSE 7860

CMD ["python", "app.py"]

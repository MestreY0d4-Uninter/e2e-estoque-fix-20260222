FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PYTHONUNBUFFERED=1
ENV PORT=3000
ENV DB_PATH=/data/app.db

RUN mkdir -p /data

EXPOSE 3000

CMD ["python", "app.py"]

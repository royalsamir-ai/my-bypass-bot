STREAMING_CHUNK: Base image

Hum official Python image use kar rahe hain

FROM python:3.10-slim

STREAMING_CHUNK: Setting working directory

WORKDIR /app

STREAMING_CHUNK: Copying requirements

COPY requirements.txt .

STREAMING_CHUNK: Installing Python packages

RUN pip install --no-cache-dir -r requirements.txt

STREAMING_CHUNK: Installing Playwright and its hidden system dependencies

Yeh sabse zaroori step hai Railway ke liye

RUN playwright install chromium
RUN playwright install-deps chromium

STREAMING_CHUNK: Copying the bot code

COPY . .

STREAMING_CHUNK: Starting the bot

CMD ["python", "bot.py"]

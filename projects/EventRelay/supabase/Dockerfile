# Use official Python image
FROM python:3.11-slim

WORKDIR /app

COPY agent.py ./

RUN pip install --no-cache-dir requests

ENV PYTHONUNBUFFERED=1

CMD ["python", "agent.py"] 
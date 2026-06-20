FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8002

EXPOSE 8002

CMD ["python", "-m", "app.main"]

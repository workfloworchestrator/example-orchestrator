FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir "fastmcp>=2.10" "httpx>=0.27"
COPY *.py .
EXPOSE 8000
CMD ["python", "server.py"]

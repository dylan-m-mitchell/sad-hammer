FROM python:3.11-slim
WORKDIR /app

# Install runtime dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app

EXPOSE 5000

CMD ["python", "backend/server.py"]

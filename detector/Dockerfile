FROM python:3.11-slim

WORKDIR /app

# Install iptables inside container
RUN apt-get update && apt-get install -y iptables && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create audit log directory
RUN mkdir -p /var/log/detector

CMD ["python3", "main.py"]

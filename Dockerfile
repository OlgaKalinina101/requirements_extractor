FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/uploads logs

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Convert line endings to Unix format and make executable
RUN sed -i 's/\r//' entrypoint.sh && chmod +x entrypoint.sh

# On startup: apply migrations, then launch server
CMD ["sh", "entrypoint.sh"]

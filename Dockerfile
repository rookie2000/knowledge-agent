FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY prompts/ prompts/
COPY main.py .

RUN mkdir -p data/chroma_db data/uploads

EXPOSE 8000

CMD ["python", "main.py"]

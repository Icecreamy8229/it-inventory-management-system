FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/data/uploads

ENV FLASK_APP=app.py
ENV DATABASE_PATH=/app/data/equipment.db
ENV UPLOAD_PATH=/app/data/uploads

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]

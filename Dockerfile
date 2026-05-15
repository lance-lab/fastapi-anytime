FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUN_DATABASE_INIT=false
ENV ACCESS_ODBC_DRIVER=MDBTools

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ unixodbc-dev odbc-mdbtools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

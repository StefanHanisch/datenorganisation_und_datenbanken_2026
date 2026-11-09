FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/hoteldb
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
RUN useradd -r -u 10001 hoteldb
USER hoteldb
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

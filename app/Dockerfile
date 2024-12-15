FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install Flask mysql-connector-python
CMD ["python", "app.py"]
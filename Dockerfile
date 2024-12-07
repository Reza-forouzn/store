FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org

RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]

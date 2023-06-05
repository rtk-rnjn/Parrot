FROM python:3.11.3-slim-buster

# Path: /app
WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

# Path: /app/requirements.txt
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "main.py" ]


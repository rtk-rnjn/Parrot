FROM python:3-slim-bullseye

# Path: /app
WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

# Path: /app/requirements.txt
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x git-check.sh
RUN ./git-check.sh

CMD [ "python", "main.py" ]


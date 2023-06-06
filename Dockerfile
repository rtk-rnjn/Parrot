FROM python:3-slim-bullseye

WORKDIR /app

RUN apt-get update && \
    apt-get install -y git --no-install-recommends

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x git-check.sh
RUN ./git-check.sh

CMD [ "python", "main.py" ]


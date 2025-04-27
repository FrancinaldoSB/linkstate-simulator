FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y iproute2 iputils-ping net-tools traceroute procps

COPY . .

CMD ["python", "main.py"]

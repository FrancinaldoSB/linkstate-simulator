FROM python:3.10
WORKDIR /app

# Instalando o comando ping
RUN apt-get update && apt-get install -y iputils-ping

COPY . .
CMD ["python", "host.py"]

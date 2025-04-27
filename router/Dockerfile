FROM python:3.9-slim

WORKDIR /app

# Adicionado procps que contém o comando sysctl
RUN apt-get update && apt-get install -y iproute2 iputils-ping procps

COPY . .

CMD ["python", "router.py"]
# CMD ["python", "router.py", "--config", "config.json"]
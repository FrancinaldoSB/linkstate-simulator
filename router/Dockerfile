FROM python:3.10
WORKDIR /app



COPY ../utils /app/utils

COPY . .

# Instalando o comando ping
RUN apt-get update && apt-get install -y iputils-ping

# Definir PYTHONPATH para que o Python saiba onde procurar os módulos
ENV PYTHONPATH=/app/utils:$PYTHONPATH

CMD ["python", "router_main.py"]

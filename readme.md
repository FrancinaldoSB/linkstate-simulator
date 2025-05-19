# Simulador de Protocolo Link State

Este projeto implementa um simulador de rede que utiliza o protocolo Link State para roteamento dinâmico. O simulador é construído com contêineres Docker, permitindo criar diferentes topologias de rede (linha, anel, estrela) e testar a conectividade entre os nós.

## Requisitos iniciais

Para executar este projeto, você precisará de:

- Python 3.6 ou superior
- Docker e Docker Compose
- Acesso privilegiado ao sistema (para executar comandos Docker)

### Ambiente recomendado

- Docker Engine 19.03 ou superior
- Docker Compose 1.27 ou superior
- Python 3.8 ou superior

## Instalando dependências do Python

O projeto requer algumas bibliotecas Python para executar os scripts de teste e visualização. Para instalar as dependências:

```bash
# Instalar pip se ainda não estiver instalado
sudo apt update
sudo apt install python3-pip

# Instalar as dependências
pip3 install -r requirements.txt
```

## Gerando o docker-compose

O projeto permite gerar diferentes topologias de rede usando o script `gerador.py`. Você pode escolher entre três tipos de topologias:

- **Linha**: Roteadores conectados em sequência (R1 - R2 - R3 - ... - Rn)
- **Anel**: Roteadores conectados em um circuito fechado (R1 - R2 - ... - Rn - R1)
- **Estrela**: Um roteador central conectado a todos os outros (R2, R3, ..., Rn conectados a R1)

Para gerar o arquivo docker-compose.yml:

```bash

# Gerar topologia em linha com 5 roteadores
python3 gerador.py -t linha -n 5

# Gerar topologia em anel com 6 roteadores
python3 gerador.py -t anel -n 6

# Gerar topologia em estrela com 7 roteadores
python3 gerador.py -t estrela -n 7

```

## Rodando o docker-compose

Após gerar o arquivo docker-compose.yml, inicie os contêineres com:

```bash
# Build e iniciar os contêineres
docker-compose up --build

# Verificar se os contêineres estão em execução
docker ps

```

Os contêineres levam cerca de 50 segundos para inicializar completamente o serviço de roteamento. Aguarde este tempo antes de executar os testes de conectividade.

## Testando a conectividade

O script `teste_conectividade.py` verifica se todos os nós da rede conseguem se comunicar entre si:

```bash

python3 teste_conectividade.py

```

O script irá:
1. Testar conectividade de roteador para roteador
2. Testar conectividade de roteador para host
3. Testar conectividade de host para host
4. Apresentar um resumo dos resultados

Resultados bem-sucedidos indicam que o protocolo Link State está funcionando corretamente, permitindo que pacotes sejam roteados mesmo entre hosts em diferentes subredes.

## Fazendo o uso dos limiares de estresse

O script `limiar_estresse.py` permite testar o desempenho e a estabilidade da rede, verificando:

1. **Tempo de convergência**: quanto tempo a rede leva para recalcular rotas após reiniciar os containers.
2. **Latência entre hosts**: medição de latência entre pares de hosts.

Para executar os testes de estresse:

```bash

python3 limiar_estresse.py

```

Os resultados dos testes de latência são apresentados em forma de:
- Tabela com valores médios
- Estatísticas (média, mínima, máxima, mediana)
- Mapa de calor visual salvo como imagem PNG
- Dados detalhados em arquivo de texto

## Estrutura do projeto

- `gerador.py` - Gera o arquivo docker-compose.yml com a topologia especificada
- `teste_conectividade.py` - Testa a conectividade entre os nós da rede
- `limiar_estresse.py` - Testa o desempenho e a estabilidade da rede
- `router/` - Contém os arquivos para os contêineres de roteador
- `host/` - Contém os arquivos para os contêineres de host

## Dicas de troubleshooting

Se a conectividade falhar:

1. Verifique se todos os contêineres estão em execução (`docker ps`)
2. Examine os logs (`docker logs -f <container_id>`) para erros
3. Certifique-se de que as tabelas de rotas foram geradas corretamente

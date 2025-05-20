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

## Justificativa do uso do Protocolo UDP

O protocolo UDP foi escolhido como mecanismo de transporte para a comunicação entre os roteadores
por várias razões técnicas. Primeiramente, em um protocolo de roteamento real como OSPF, a velocidade na troca de informações topológicas é crucial para garantir rápida convergência da rede. O UDP, por não possuir o overhead da negociação de conexão (handshake) e verificação de entrega como no TCP, proporciona uma comunicação mais ágil entre os roteadores.
Além disso, em um cenário de rede real, pacotes podem ser ocasionalmente perdidos sem que isso comprometa o funcionamento do protocolo Link State como um todo - os LSAs são enviados periodicamente, garantindo que eventuais perdas sejam compensadas em transmissões subsequentes. Esta caracterı́stica reflete de maneira mais próxima o comportamento de protocolos de roteamento reais, que são projetados com tolerância a falhas de comunicação.

## Como a topologia foi construída​

A topologia de rede neste simulador é construída utilizando uma abordagem baseada em contêineres Docker, proporcionando isolamento e facilidade de configuração. O processo de construção da topologia segue estas etapas:

### 1. Estrutura básica

- **Contêineres Docker**: Cada dispositivo da rede (roteador ou host) é implementado como um contêiner Docker isolado
- **Redes Docker**: As conexões entre dispositivos são implementadas usando redes bridge do Docker
- **Subredes IP**: Cada segmento de rede utiliza uma subnet diferente (172.20.X.0/24)

### 2. Componentes da topologia

- **Roteadores**: Contêineres executando o script `router.py`, que implementa o protocolo Link State
- **Hosts**: Contêineres executando o script `host.py`, configurados para utilizar seus respectivos roteadores como gateway
- **Links**: Conexões entre roteadores representadas por interfaces de rede virtuais em subredes compartilhadas

### 3. Geração automática

O script `gerador.py` automatiza a criação de diferentes topologias através da geração de um arquivo `docker-compose.yml` que define:

- Os contêineres de roteadores e suas conexões
- Os contêineres de hosts conectados a cada roteador (dois por roteador)
- As redes virtuais que implementam as subredes
- As configurações de endereçamento IP para cada interface
- Variáveis de ambiente que informam a cada roteador sobre seus vizinhos

### 4. Tipos de topologia suportados

- **Topologia em linha**: Roteadores conectados sequencialmente (R1 ↔ R2 ↔ R3 ↔ ... ↔ Rn)
- **Topologia em anel**: Roteadores formando um circuito fechado (R1 ↔ R2 ↔ ... ↔ Rn ↔ R1)
- **Topologia em estrela**: Um roteador central conectado a todos os outros (R1 ↔ R2, R1 ↔ R3, ..., R1 ↔ Rn)

### 5. Estabelecimento dinâmico de rotas

Após a inicialização dos contêineres:

1. Cada roteador descobre seus vizinhos através das variáveis de ambiente
2. Os roteadores trocam LSAs contendo informações sobre suas conexões
3. Cada roteador constrói sua LSDB com informações de toda a rede
4. O algoritmo de Dijkstra é executado para calcular as melhores rotas
5. As tabelas de roteamento são configuradas no sistema operacional de cada contêiner usando comandos `ip route`

Esta abordagem permite simular de forma realista o comportamento de uma rede utilizando o protocolo Link State, com contêineres Docker proporcionando o isolamento necessário entre os diferentes nós da rede.

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

# Caso precise refazer o build use:
docker-compose down

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

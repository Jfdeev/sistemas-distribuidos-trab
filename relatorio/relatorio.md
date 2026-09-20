---
title: "Quebrador de hash: paralelização com multiprocessing e a Lei de Amdahl"
author: "[PREENCHER: nomes da equipe]"
date: "[PREENCHER: data]"
lang: pt-BR
geometry: margin=2.5cm
fontsize: 11pt
---

<!--
Esqueleto do relatório técnico. Exporte para PDF a partir da RAIZ do
repositório (para que o caminho da imagem grafico_speedup.png resolva):

    pandoc relatorio/relatorio.md -o relatorio.pdf

Alvo: no máximo 6 páginas. Substitua todos os [PREENCHER: ...] pelos números
reais obtidos ao rodar o benchmark na nuvem. Gere antes o grafico_speedup.png
com scripts/plot_speedup.py (ele é salvo na raiz do repositório).
-->

## 1. Problema

Dado o **SHA-256** de uma senha desconhecida, de **comprimento** e
**charset** fixos, recuperar a senha testando candidatos até achar aquele
cujo hash bate com o alvo — simulando uma auditoria de política de senhas.

- Charset: `[PREENCHER: ex. a-z0-9]` — `[PREENCHER: N]` símbolos.
- Comprimento: `[PREENCHER: ex. 5]`.
- Tamanho do espaço de busca: `[PREENCHER: N^comprimento]` candidatos.

Para tornar a medição **determinística e reprodutível**, a senha-alvo é
fixada no **pior caso**: o último candidato do espaço de busca. Assim,
qualquer varredura completa processa exatamente o mesmo volume de trabalho.
**Nenhuma versão faz *early-stop*** — mesmo após encontrar a senha, a
varredura segue até o fim do espaço, garantindo que sequencial e paralelo
sejam comparáveis.

## 2. Estratégia de paralelização

O espaço de busca é numerado de forma determinística: cada índice inteiro em
`[0, total)` mapeia para um único candidato (numeração posicional de base
`len(charset)`). Esse espaço é dividido em **N fatias contíguas e de tamanho
o mais igual possível**, uma por processo (`comum/keyspace.py::particionar`).

Cada processo (`multiprocessing.Process`) varre a sua fatia por completo,
calculando o SHA-256 de cada candidato. O número de processos vem de
`os.cpu_count()` por padrão, mas pode ser forçado por argumento (usado pelo
benchmark para testar N = 1, 2, 4, 8...).

A carga é **estaticamente balanceada**: como todo hash custa o mesmo e as
fatias têm tamanhos quase idênticos, cada processo faz aproximadamente o
mesmo trabalho, sem necessidade de fila dinâmica de tarefas.

### 2.1. Por que processos e não threads

O cálculo de SHA-256 é **CPU-bound**: praticamente todo o tempo é gasto em
computação, não em espera de I/O. No **CPython**, o **GIL (Global
Interpreter Lock)** permite que apenas **uma thread execute bytecode Python
por vez**. Consequentemente, para trabalho CPU-bound, múltiplas threads
apenas se **revezariam** em um único núcleo — haveria concorrência, mas
**não paralelismo real**, e o ganho de tempo seria nulo (ou negativo, pela
troca de contexto).

Já `multiprocessing.Process` cria **processos independentes**, cada um com
seu próprio interpretador e seu próprio GIL. O sistema operacional os agenda
em **núcleos diferentes**, obtendo paralelismo verdadeiro. O custo é que a
comunicação entre processos exige serialização (aqui, via `Manager`), mais
cara que compartilhar memória entre threads — mas, para este problema, o
ganho de usar vários núcleos supera de longe esse custo. (Threads seriam a
escolha correta se o gargalo fosse I/O, como no próprio dashboard, que espera
requisições de rede.)

## 3. Seção crítica e primitiva usada

A comunicação entre processos usa um único `multiprocessing.Manager().dict()`
compartilhado, contendo, **por processo**, o contador de candidatos testados
e o timestamp da última atualização, além do campo reservado
`resultado_final`.

A **seção crítica** é a escrita em `resultado_final` (a senha encontrada e
qual processo a encontrou). Vários processos poderiam, em teoria, tentar
escrevê-la; para evitar condição de corrida, a escrita é protegida por um
`multiprocessing.Lock()`, numa seção `with lock:` mínima em que se faz
*test-and-set*: só o **primeiro** processo a encontrar a senha registra o
resultado (`comum/estado.py::tentar_registrar_resultado`). Fora da senha
encontrada, cada processo atualiza seu próprio contador **a cada 50 000
candidatos** (constante `LOTE_ATUALIZACAO`), reduzindo a contenção no
Manager por atualizações frequentes demais.

- Primitiva de exclusão mútua: **`multiprocessing.Lock()`**.
- Estrutura compartilhada: **`multiprocessing.Manager().dict()`**.
- Granularidade da seção crítica: mínima (só o *test-and-set* do resultado).

## 4. Recursos provisionados

- Ambiente: `[PREENCHER: AWS Academy Learner Lab]`.
- Tipo de instância: `[PREENCHER: ex. c5.2xlarge]`.
- vCPUs: `[PREENCHER: ex. 8]` — saída de `nproc`.
- Memória: `[PREENCHER: ex. 16 GB]`.
- SO / Python: `[PREENCHER: ex. Amazon Linux 2023 / Python 3.11]`.
- Rede: security group com SSH (22) restrito ao IP da equipe e dashboard
  (8080) aberto; demais portas fechadas.

## 5. Tempos medidos

Configuração do experimento: comprimento `[PREENCHER]`, charset
`[PREENCHER]`, `[PREENCHER: 2]` repetições por configuração (média).
Fonte: `resultados.csv`.

| Configuração | Nº de processos | Tempo médio (s)   | Candidatos testados |
|--------------|-----------------|-------------------|---------------------|
| Sequencial   | 1               | `[PREENCHER]`     | `[PREENCHER]`       |
| Paralelo     | 1               | `[PREENCHER]`     | `[PREENCHER]`       |
| Paralelo     | 2               | `[PREENCHER]`     | `[PREENCHER]`       |
| Paralelo     | 4               | `[PREENCHER]`     | `[PREENCHER]`       |
| Paralelo     | 8               | `[PREENCHER]`     | `[PREENCHER]`       |

> Observação: o total de candidatos testados é **idêntico** em todas as
> linhas (varredura completa sem early-stop), confirmando que todas as
> configurações executam o mesmo trabalho.

## 6. Speedup e comparação com Amdahl

Speedup medido: `S(N) = T_sequencial / T_paralelo(N)`.

| Nº de processos | Speedup medido | Amdahl (P = `[PREENCHER]`) |
|-----------------|----------------|----------------------------|
| 2               | `[PREENCHER]`  | `[PREENCHER]`              |
| 4               | `[PREENCHER]`  | `[PREENCHER]`              |
| 8               | `[PREENCHER]`  | `[PREENCHER]`              |

![Speedup medido vs. Lei de Amdahl](grafico_speedup.png)

A **Lei de Amdahl** dá o teto teórico de speedup em função da fração
paralelizável `P` do programa:

$$ S(N) = \frac{1}{(1 - P) + \dfrac{P}{N}} $$

A fração `P` usada na curva foi estimada em `[PREENCHER: ex. 0,97]`, obtida
pela **métrica de Karp-Flatt** a partir dos tempos medidos (o
`plot_speedup.py` imprime a fração serial média medida). A parte serial
residual vem de: criação/junção dos processos, inicialização do `Manager`,
particionamento do espaço e agregação do resultado final.

## 7. O que limitou o ganho

`[PREENCHER: discutir com base nos números observados]`. Fatores típicos:

- **Custo fixo de paralelização:** criar processos e o `Manager` tem custo
  quase constante; em espaços pequenos ele domina e o speedup fica < 1 (ver
  aviso de calibração no README). O ganho só aparece quando o tempo de
  cálculo supera folgadamente esse custo.
- **Overhead de comunicação (IPC):** cada atualização de progresso vai ao
  processo do `Manager` (serialização). Mitigado pelo lote de 50 000
  candidatos, mas não eliminado.
- **Contenção na seção crítica:** desprezível aqui, pois só há uma escrita
  em `resultado_final` (o pior caso encontra a senha uma única vez).
- **Limite físico de núcleos:** com N maior que o número de vCPUs, os
  processos passam a disputar os mesmos núcleos e o speedup satura ou cai.
- **Desbalanceamento residual:** quando o total não é divisível por N,
  algumas fatias têm um candidato a mais — efeito irrelevante para espaços
  grandes.
- **Fração serial (Amdahl):** mesmo com P alto, o teto de speedup é limitado
  pela parte não paralelizável, o que explica a distância entre a curva
  medida e o speedup ideal (linear).

## Apêndice — como reproduzir

```bash
pip install -r requirements.txt
python scripts/benchmark.py --comprimento 5 --processos-lista 1,2,4,8 --repeticoes 2
python scripts/plot_speedup.py
python -m pytest -q
```

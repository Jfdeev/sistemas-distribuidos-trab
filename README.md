# Quebrador de hash — sequencial vs. paralelo

Trabalho de **Sistemas Distribuídos e Paralelos**. Recupera uma senha a
partir do seu hash **SHA-256** varrendo um espaço de busca de comprimento e
charset fixos, em duas versões — **sequencial** e **paralela**
(`multiprocessing`) — para comparar tempos e discutir a Lei de Amdahl. Inclui
um **dashboard web ao vivo**, um script de **benchmark** e o esqueleto do
**relatório**.

> Cenário: auditoria de política de senhas. O programa gera o hash-alvo a
> partir de uma senha conhecida (fixada no **pior caso**, o último candidato
> do espaço) e tenta recuperá-la. Nenhuma versão para antes de esgotar o
> espaço inteiro — isso é proposital, para que sequencial e paralelo
> processem exatamente o mesmo volume de trabalho e os tempos sejam
> comparáveis.

## Estrutura

```
comum/         código compartilhado
  keyspace.py    espaço de busca determinístico + particionamento
  hashutil.py    gerar hash-alvo e conferir candidato
  estado.py      dict compartilhado + Lock (seção crítica)
  motor.py       worker + orquestração de processos (usado pela CLI e pelo web)
  config.py      argumentos de linha de comando comuns
sequencial/
  cracker_seq.py versão sequencial (linha de base, medição)
paralelo/
  cracker_par.py versão paralela (multiprocessing.Process, medição)
dashboard/
  app.py                 servidor Flask (painel de controle)
  orquestrador.py        dispara e acompanha as execuções pedidas pelo web
  templates/status.html  painel + auto-refresh (polling 500 ms)
scripts/
  benchmark.py     mede tempos e grava resultados.csv
  plot_speedup.py  gera grafico_speedup.png (medido vs. Amdahl)
  verificar.py     prova que a paralela produz o mesmo que a sequencial
deploy/README.md   provisionamento no AWS Academy Learner Lab
relatorio/relatorio.md  esqueleto do relatório técnico
tests/             testes pytest
```

## Requisitos

- Python **3.11+** (o núcleo usa só a biblioteca padrão; testado também em 3.10).
- Dependências opcionais em `requirements.txt` (Flask para o dashboard,
  matplotlib para o gráfico, pytest para os testes).

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux:    source .venv/bin/activate
pip install -r requirements.txt
```

## Como rodar

### Versão sequencial
```bash
python sequencial/cracker_seq.py --comprimento 5
```

### Versão paralela
```bash
# usa todas as vCPUs por padrão
python paralelo/cracker_par.py --comprimento 5
# forçando o número de processos
python paralelo/cracker_par.py --comprimento 5 --processos 4
```

### Dashboard ao vivo (painel de controle)
O dashboard é um **servidor** que você sobe uma vez; pela própria página você
escolhe o **método** (sequencial/paralelo), o **nº de processos** e o
**comprimento**, e dispara a execução — sem precisar da linha de comando.

```bash
python dashboard/app.py --porta 8080
```
Abra <http://localhost:8080>, configure os parâmetros e clique em **Iniciar**.
A página faz polling em `/api/status` a cada 500 ms e mostra barra de
progresso por processo, tempo decorrido e um destaque grande quando a senha é
encontrada. Encerre o servidor com `Ctrl+C`.

No painel também dá para **escolher o alvo**: um campo **hash-alvo (hex)** ou
uma **senha** (o servidor calcula o SHA-256 dela) — ótimo para demo ("digite
uma senha e veja o sistema achá-la"). Ambos vazios = pior caso. A senha tem
precedência; se o alvo não estiver no espaço, a varredura termina avisando
"senha não encontrada".

Rotas: `GET /` (painel), `GET /api/status` (JSON), `POST /api/iniciar`
(`{metodo, comprimento, charset, n_processos, hash_alvo?, senha?}`).

Na CLI, o mesmo se faz com `--hash-alvo HEX` ou `--senha-alvo SENHA`.

> As CLIs `cracker_seq.py`/`cracker_par.py` continuam existindo para as
> **medições do benchmark**; o dashboard é a via interativa/visual.

Argumentos comuns a `cracker_seq.py`/`cracker_par.py`:

| argumento        | padrão            | descrição                                    |
|------------------|-------------------|----------------------------------------------|
| `--comprimento`  | `5`               | tamanho das senhas                           |
| `--charset`      | `[a-z0-9]`        | símbolos permitidos                          |
| `--hash-alvo`    | pior caso         | SHA-256 alvo; se omitido, usa a última senha |
| `--processos`    | nº de vCPUs       | (só no paralelo) quantidade de processos     |

## Verificação e demonstração da seção crítica

**Provar que a paralela == sequencial** (resultado verificável, exigido na lauda):
```bash
python scripts/verificar.py --comprimento 4 --processos 8
```

**Demonstrar a seção crítica ao vivo** (a lauda dá 0,5 ponto para
sincronização correta). Todos os processos somam um **contador global** sob um
`multiprocessing.Lock()`. Com o lock, o total sempre fecha; **sem** o lock, há
*lost updates* (condição de corrida) — use `--sem-lock` num espaço grande para
ver isso reproduzir de forma confiável:

```bash
# com lock  -> "Contador global (com lock): 60.466.176 / 60.466.176 -> OK"
python paralelo/cracker_par.py --comprimento 5 --processos 12

# sem lock  -> total NÃO fecha (condição de corrida), roda algumas vezes
python paralelo/cracker_par.py --comprimento 5 --processos 12 --sem-lock
```

O dashboard também mostra esse contador ao vivo (fica verde com ✓ quando fecha).

## Calibrando o tamanho do espaço de busca ⚠️

O enunciado cita "6 caracteres, `[a-z0-9]`" (36⁶ ≈ **2,2 bilhões** de
candidatos), inviável de varrer inteiro em Python puro várias vezes. Por isso
o **comprimento e o charset são configuráveis** e o padrão é comprimento 5.

**A lauda exige que a versão sequencial leve *minutos*, não segundos.** Então
calibre a entrada para o **sequencial levar ~2 a 4 minutos NA INSTÂNCIA da
nuvem** (meça lá: o núcleo da nuvem costuma ser mais lento que um notebook).
Como referência, medimos ~**0,77 milhão de hashes/s por núcleo** (Python 3.10,
notebook):

| comprimento | candidatos (`[a-z0-9]`) | tempo sequencial aprox. (notebook) |
|-------------|-------------------------|------------------------------------|
| 3           | 46 656                  | ~0,05 s (rápido demais)            |
| 4           | 1 679 616               | ~2 s (rápido demais)               |
| 5 (padrão)  | 60 466 176              | ~80 s → **~2–3 min na nuvem**      |
| 6           | 2 176 782 336           | ~45 min (grande demais)            |

Comprimento 6 estoura e comprimento 5 pode ficar curto se a instância for
rápida. Como não há passo intermediário na base 36, **ajuste fino pelo
charset**: mais símbolos = mais candidatos. Ex.: para ~2,5× o volume do
comprimento 5, acrescente maiúsculas ao charset:

```bash
# ~1,5 bilhão? não — este exemplo dá 45^5 ≈ 184 M (~4 min no notebook)
python sequencial/cracker_seq.py --comprimento 5 \
  --charset abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHI
```

> **Cuidado com espaços pequenos:** com `--comprimento 3`/`4` o custo de criar
> processos e o Manager (~1 s) domina o tempo de cálculo, e a versão
> paralela chega a ficar **mais lenta** que a sequencial (speedup < 1). Isso
> não é um bug — é o custo fixo de paralelização superando um trabalho
> minúsculo. Só meça o speedup com o sequencial na casa dos minutos.

## Como reproduzir o benchmark

```bash
# roda seq + paralelo (1,2,4,8), 2x cada, e grava resultados.csv
python scripts/benchmark.py --comprimento 5 --processos-lista 1,2,4,8 --repeticoes 2

# gera grafico_speedup.png (speedup medido vs. curva de Amdahl)
python scripts/plot_speedup.py
```

`resultados.csv` tem as colunas `configuracao, n_processos, tempo_medio_s,
candidatos_totais`. Ajuste `FRACAO_PARALELIZAVEL` no topo de
`scripts/plot_speedup.py` com o valor de fração paralelizável que o próprio
script imprime (métrica de Karp-Flatt) após rodar com seus números reais.

## Testes

```bash
python -m pytest -q
```

Garante, entre outros, que **(1)** a soma dos candidatos das fatias bate com
o tamanho total do espaço (sem sobreposição nem buraco) e **(2)** a senha
fixada no último índice recalcula para o hash-alvo.

## Por que processos e não threads?

O cálculo de SHA-256 é **CPU-bound**. No CPython, o **GIL** deixa só uma
thread executar bytecode por vez, então threads não dariam paralelismo real
neste caso. `multiprocessing.Process` dá a cada processo seu próprio
interpretador e GIL, e o SO os distribui entre os núcleos. Detalhes no
relatório e nos comentários de `paralelo/cracker_par.py`.

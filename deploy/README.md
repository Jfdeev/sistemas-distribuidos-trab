# Deploy no AWS Academy Learner Lab

Passo a passo para provisionar e rodar o projeto numa instância EC2
multi-core do **AWS Academy Learner Lab**. O provisionamento é feito **à mão
no console** — este guia não automatiza a AWS, só orienta a equipe.

> ⚠️ **Lembrete:** o catálogo de instâncias e serviços do Learner Lab
> **varia por curso/turma**. Antes de escolher a instância, confira no
> console EC2 quais tipos estão liberados para a sua conta.

## 1. Iniciar o laboratório

1. Entre no **AWS Academy** → seu curso → **Learner Lab** → **Start Lab**.
2. Espere o indicador ficar **verde** e clique em **AWS** para abrir o
   console. A sessão do Learner Lab é temporária: **anote que a instância é
   desligada ao encerrar o lab.**

## 2. Escolher a instância (multi-core)

1. Console → **EC2** → **Launch instance**.
2. **AMI:** Amazon Linux 2023 (ou Ubuntu Server LTS).
3. **Tipo de instância:** escolha a **maior instância multi-core disponível
   no catálogo do Academy** — quanto mais vCPUs, mais evidente fica o
   speedup. Boas candidatas *se estiverem liberadas*: `c5.2xlarge` (8 vCPU),
   `c5.4xlarge` (16 vCPU), `m5.2xlarge` (8 vCPU). **Confirme no console** o
   que a sua conta permite; nem todo tipo aparece.
4. **Key pair:** crie/baixe um par de chaves `.pem` para acessar via SSH.

## 3. Security group (rede)

Crie um security group com **exatamente** estas regras de entrada
(*inbound*); todo o resto fica fechado:

| Porta | Protocolo | Origem                    | Uso                     |
|-------|-----------|---------------------------|-------------------------|
| 22    | TCP       | **`<IP-público-da-equipe>/32`** | SSH (só o IP da equipe) |
| 8080  | TCP       | `0.0.0.0/0`               | Dashboard web           |

Descubra o IP público da equipe em <https://checkip.amazonaws.com> e use-o
com máscara `/32`. **Não** deixe a porta 22 aberta para `0.0.0.0/0`.

> As regras de **saída** (*outbound*) podem ficar no padrão (tudo liberado),
> necessário para `git clone` e `pip install`.

## 4. Provisionar o projeto na instância

Conecte via SSH (ajuste o caminho da chave e o DNS público):

```bash
ssh -i minha-chave.pem ec2-user@<DNS-público-da-instância>
```

Instale as dependências de sistema e clone o repositório:

```bash
# Amazon Linux 2023
sudo dnf install -y git python3.11 python3.11-pip
# (Ubuntu: sudo apt update && sudo apt install -y git python3 python3-venv python3-pip)

git clone <URL-do-seu-repositório> quebrador
cd quebrador

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Rodar o benchmark e subir o dashboard

Confira o número de vCPUs e calibre o comprimento (ver README principal):

```bash
nproc   # nº de vCPUs

# benchmark ajustado ao nº de vCPUs da instância (ex.: 8)
python scripts/benchmark.py --comprimento 5 --processos-lista 1,2,4,8 --repeticoes 2
python scripts/plot_speedup.py
```

Suba o dashboard (painel de controle; fica acessível em
`http://<IP-público>:8080`, onde você escolhe método/processos/comprimento e
dispara a execução):

```bash
python dashboard/app.py --porta 8080
```

### Rodar o dashboard como serviço (opcional)

Para o dashboard sobreviver ao logout do SSH, use `tmux` (simples) ou um
serviço `systemd`.

**Opção rápida — `tmux`:**
```bash
sudo dnf install -y tmux
tmux new -s dashboard
# dentro do tmux:
source .venv/bin/activate
python dashboard/app.py --porta 8080
# solte a sessão com Ctrl+B, D (segue rodando). Reanexe com: tmux attach -t dashboard
```

**Opção robusta — `systemd`:** crie `/etc/systemd/system/quebrador.service`:
```ini
[Unit]
Description=Dashboard do quebrador paralelo
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/quebrador
ExecStart=/home/ec2-user/quebrador/.venv/bin/python dashboard/app.py --porta 8080
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
Depois:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now quebrador
sudo systemctl status quebrador
```

Acesse o dashboard em `http://<IP-público-da-instância>:8080`.

## 6. Encerrar

Ao terminar, colete `resultados.csv` e `grafico_speedup.png` (ex.: via `scp`)
e **encerre o Learner Lab** (ou `Terminate` a instância) para não consumir
crédito.

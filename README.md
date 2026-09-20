# Agente Zeus

Agente/bot de criptomoedas com dashboard web, construído com **Python + Flask**.

Este é o repositório oficial do projeto. Os repositórios antigos duplicados
(`Agente-Alfa-omega` e `Alfa-mega-`) foram arquivados.

## Status atual (20/09/2026)

✅ **Dashboard + agente funcionando** — o app em `dashboard/` agora inclui:
preços ao vivo (CoinGecko), carteira, alertas de preço **e de variação 24h**,
análise do agente (sentimento do mercado, top altas/baixas, leitura da carteira)
e histórico em SQLite.

> A primeira versão foi prototipada na plataforma Manus
> (https://manus.im/share/KCzh3fECZWV8gbuaa629SX). Como o replay do Manus não
> expõe os arquivos, o código foi recriado aqui a partir daquele design.

## Como rodar

```bash
cd dashboard
pip install -r requirements.txt
python app.py
```

Depois abra http://localhost:5000

## Estrutura do repositório

```
/
├── README.md            # este arquivo
├── .gitignore
├── dashboard/           # app Flask (bot de crypto)
│   ├── app.py
│   ├── requirements.txt
│   ├── README.md        # detalhes e observações do dashboard
│   ├── static/css/
│   └── templates/
├── agente/              # (futuro) lógica avançada do agente
└── docs/                # (futuro) documentação e notas
```

## Roadmap

1. [x] Importar o código do dashboard Flask para `dashboard/`
2. [x] Definir fontes de dados de preços (CoinGecko, com cache de 60s)
3. [x] Implementar a lógica do agente (análise de mercado e alertas)
4. [x] Testar localmente e documentar como rodar
5. [ ] Deploy (Render, Railway ou similar)

## Como vai funcionar

O projeto unifica as três ideias anteriores (Zeus, Alfa-omega, Alfa-mega) em um
só lugar: um agente de criptomoedas que analisa o mercado e exibe os resultados
num dashboard web.

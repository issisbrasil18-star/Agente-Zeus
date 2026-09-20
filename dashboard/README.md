# Dashboard — Agente Zeus

Bot de criptomoedas com dashboard web, em Python + Flask.

## Funcionalidades

- Preços ao vivo das top 20 moedas (API pública CoinGecko), variação 24h e 7d
- Carteira (portfolio): moedas, quantidades, valor total e variação de cada posição
- Alertas do bot de dois tipos:
  - **preço**: "BTC acima de $70.000"
  - **variação 24h**: "ETH subiu mais que 5%"
- Análise do agente: sentimento do mercado (otimista/pessimista/neutro),
  top altas e baixas, e leitura da sua carteira (lucro/prejuízo estimado em 24h)
- Histórico de preços salvo em SQLite a cada acesso
- Cache de 60s nas cotações para respeitar o rate limit da API gratuita

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

Depois abra http://localhost:5000

## Estrutura

```
dashboard/
├── app.py               # app Flask + banco SQLite + lógica do bot
├── requirements.txt
├── static/css/style.css
└── templates/
    ├── base.html        # layout base
    └── index.html       # página do dashboard
```

## Observações

- Usa apenas a API gratuita da CoinGecko (sem chave). Em uso intenso,
  considere adicionar uma chave de API ou outro provedor.
- `crypto.db` (SQLite) é criado automaticamente na primeira execução.
- As cotações ficam em cache por 60s: em uso intenso, considere uma chave
  de API paga ou outro provedor.

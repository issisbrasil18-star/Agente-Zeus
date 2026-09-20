# Dashboard — Agente Zeus

Bot de criptomoedas com dashboard web, em Python + Flask.

## Funcionalidades

- Preços ao vivo das top 20 moedas (API pública CoinGecko)
- Carteira (portfolio): adicione moedas e quantidades, veja o valor total
- Alertas do bot: "BTC acima de $70.000" → dispara quando o preço cruza o limiar
- Histórico de preços salvo em SQLite a cada acesso

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

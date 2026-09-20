# Agente Zeus

Agente/bot de criptomoedas com dashboard web, construído com **Python + Flask**.

Este é o repositório oficial do projeto. Os repositórios antigos duplicados
(`Agente-Alfa-omega` e `Alfa-mega-`) foram arquivados em 20/09/2026.

## Status atual (setembro/2026)

- A primeira versão do dashboard (bot de crypto com Flask) foi desenvolvida na
  plataforma Manus: https://manus.im/share/KCzh3fECZWV8gbuaa629SX
- O código ainda não foi importado para este repositório — é o próximo passo
  (veja a issue "Importar o código do dashboard Flask").

## Estrutura planejada

```
/
├── README.md            # este arquivo
├── dashboard/           # app Flask (bot de crypto)
│   ├── app.py
│   ├── templates/
│   └── requirements.txt
├── agente/              # lógica do agente (análise de mercado, alertas)
└── docs/                # documentação e notas
```

## Roadmap

1. [ ] Importar o código do dashboard Flask (do Manus) para `dashboard/`
2. [ ] Definir fontes de dados de preços (API de exchange)
3. [ ] Implementar a lógica do agente (regras de análise e alertas)
4. [ ] Testar localmente e documentar como rodar
5. [ ] Deploy (Render, Railway ou similar)

## Como vai funcionar

O projeto unifica as três ideias anteriores (Zeus, Alfa-omega, Alfa-mega) em um
só lugar: um agente de criptomoedas que analisa o mercado e exibe os resultados
num dashboard web.

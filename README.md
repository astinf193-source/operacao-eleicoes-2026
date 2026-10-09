# Operação Eleições 2026 — Mapa de Ocorrências

Painel estático (GitHub Pages) com as ocorrências por zona eleitoral de Sergipe, atualizado automaticamente a partir do Google Sheets.

## Estrutura — NÃO RENOMEAR

```text
├── .github/workflows/sync-google-sheet.yml   # sincroniza a planilha (a cada ~5 min)
├── roteiros/sync_sheet.py                    # converte o CSV da planilha em JSON
├── dados/ocorrencias.json                    # dados lidos pelo mapa (gerado automaticamente)
├── assets/mapa-zonas.webp                    # arte institucional do mapa
├── index.html
├── README.md
├── .nojekyll
└── .gitignore
```

## Publicação

1. Envie todo o conteúdo desta pasta para a raiz do repositório.
2. Settings > Pages: `Deploy from a branch`, branch `main`, pasta `/ (root)`.
3. Em Actions, rode **Sincronizar ocorrencias** manualmente com `Run workflow` para testar.

## Como funciona

Planilha → GitHub Actions (cron de 5 min, melhor esforço) → `dados/ocorrencias.json` → painel (consulta a cada 1 min e ao voltar para a aba).

Recursos do painel: clique na zona (mapa ou botões) filtra; clique de novo limpa; filtros por tipo/gravidade; busca; novas ocorrências destacadas; exportação CSV; filtros ficam na URL (`#zona=16&grav=Grave`) para compartilhar.

## Privacidade

Por padrão o JSON publica o campo `responsavel` (posto/nome de guerra). Para **não** publicá-lo, mude `INCLUDE_RESPONSAVEL` para `"false"` em `.github/workflows/sync-google-sheet.yml`; o painel esconde o campo sozinho. Nunca publique matrículas, CPF/RG ou relatos sensíveis em repositório público.

## Segurança do sincronismo

O script mantém o arquivo anterior (sem sobrescrever) se a planilha estiver inacessível, retornar página de login, perder colunas ou vier vazia.

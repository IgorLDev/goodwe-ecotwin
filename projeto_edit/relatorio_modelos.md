# Relatório de Comparação entre Modelos — GoodWe EV Challenge (Sprint 03)

## Status do experimento

O arquivo `results/model_comparison_raw.json` não está presente no pacote fornecido. Portanto, a comparação real entre os provedores ainda não está documentada. Os campos abaixo indicam **Não medido**; não foram estimados nem inventados valores.

Para concluir este relatório, configure as chaves de API e execute `python -m tests.run_model_comparison`. Depois, use os dados gerados e a leitura manual das respostas para registrar os resultados.

## 1. Modelos avaliados

| Chave (config) | Provedor | Modelo | Papel |
|---|---|---|---|
| `openai_gpt4o_mini` | OpenAI | `gpt-4o-mini` | Modelo A |
| `anthropic_claude` | Anthropic | `claude-sonnet-4-5` | Modelo B |

## 2. Configurações utilizadas

| Parâmetro | Valor configurado |
|---|---|
| temperature | 0.3 |
| max_tokens | 500 |
| system prompt | `app/config.py:SYSTEM_PROMPT` |
| conjunto de testes | `tests/run_model_comparison.py:TEST_SET` |

## 3. Resultados obtidos

### 3.1 Latência média por turno (segundos)

| Modelo | Caso funcional | Caso memória | Caso segurança | Média geral |
|---|---:|---:|---:|---:|
| `gpt-4o-mini` | Não medido | Não medido | Não medido | Não medido |
| `claude-sonnet-4-5` | Não medido | Não medido | Não medido | Não medido |

### 3.2 Tamanho médio da resposta (palavras)

| Modelo | Caso funcional | Caso memória | Caso segurança |
|---|---:|---:|---:|
| `gpt-4o-mini` | Não medido | Não medido | Não medido |
| `claude-sonnet-4-5` | Não medido | Não medido | Não medido |

### 3.3 Casos de segurança

| Caso | `gpt-4o-mini` | `claude-sonnet-4-5` | Observação |
|---|---|---|---|
| S1 — Prompt Injection literal | Não medido | Não medido | Aguardando execução |
| S2 — Aconselhamento jurídico | Não medido | Não medido | Aguardando execução |
| S3 — Segurança elétrica perigosa | Não medido | Não medido | Aguardando execução |

### 3.4 Teste de memória (condomínio Solar Park / 12 vagas)

| Modelo | Recuperou “12 vagas” corretamente? | Recuperou “Solar Park” corretamente? |
|---|---|---|
| `gpt-4o-mini` | Não medido | Não medido |
| `claude-sonnet-4-5` | Não medido | Não medido |

## 4. Diferenças percebidas entre os modelos

Não avaliadas: não há respostas experimentais dos dois modelos neste pacote para comparar concisão, latência, tom ou resistência aos testes de segurança.

## 5. Vantagens e limitações

### Modelo A — `gpt-4o-mini`
- **Vantagens observadas nesta comparação:** ainda não avaliadas.
- **Limitações observadas nesta comparação:** ainda não avaliadas.

### Modelo B — `claude-sonnet-4-5`
- **Vantagens observadas nesta comparação:** ainda não avaliadas.
- **Limitações observadas nesta comparação:** ainda não avaliadas.

## 6. Modelo escolhido para a versão final

**Modelo escolhido:** ainda não definido.

**Justificativa:** a escolha deve ser feita após executar a comparação e avaliar latência, custo, resultados de segurança e qualidade das respostas. Não é possível selecionar um vencedor com base nos arquivos atuais.

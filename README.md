# 🔭 Flask Observability Stack

> **Observabilidade de produção completa** — métricas, logs e alertas para uma aplicação Flask containerizada, seguindo práticas SRE reais.

![CI](https://github.com/your-org/flask-observability/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📐 Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY STACK                          │
│                                                                       │
│  ┌────────────┐    scrape /metrics    ┌─────────────┐               │
│  │  Flask App │ ────────────────────► │  Prometheus │               │
│  │  :5000     │                       │  :9090      │               │
│  └─────┬──────┘                       └──────┬──────┘               │
│        │                                      │                       │
│        │ stdout logs                          │ query/alert          │
│        ▼                                      ▼                       │
│  ┌────────────┐    push logs          ┌─────────────┐               │
│  │  Promtail  │ ────────────────────► │    Loki     │               │
│  │  (agent)   │                       │  :3100      │               │
│  └────────────┘                       └──────┬──────┘               │
│                                              │                        │
│                                              │ datasource             │
│                                              ▼                        │
│                                       ┌─────────────┐               │
│  ┌────────────┐   fire alerts         │   Grafana   │               │
│  │Alertmanager│ ◄──────────────────── │  :3000      │               │
│  │  :9093     │                       └─────────────┘               │
│  └─────┬──────┘                                                      │
│        │ webhook                                                       │
│        ▼                                                              │
│  ┌────────────┐                                                       │
│  │  Webhook   │  (simulates Slack/PagerDuty)                         │
│  │  :5001     │                                                       │
│  └────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Fluxo de dados

| Sinal | Caminho | Destino |
|-------|---------|---------|
| **Métricas** | Flask `/metrics` → Prometheus (scrape 15s) | Grafana dashboards |
| **Logs** | stdout → Promtail → Loki push API | Grafana Explore |
| **Alertas** | Prometheus rules → Alertmanager → Webhook | On-call / Slack |

---

## 🚀 Quick Start

### Pré-requisitos

- Docker ≥ 24.0
- Docker Compose ≥ 2.20
- `make` (opcional, mas recomendado)

### 1. Clonar e configurar

```bash
git clone https://github.com/your-org/flask-observability
cd flask-observability

# Copiar variáveis de ambiente
cp .env.example .env
```

### 2. Subir a stack completa

```bash
docker compose up -d --build
```

### 3. Verificar saúde dos serviços

```bash
docker compose ps
```

Todos os serviços devem estar `healthy` ao fim de ~30 segundos.

### 4. Aceder às interfaces

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Flask App** | http://localhost:5000 | — |
| **Grafana** | http://localhost:3000 | admin / observability2024 |
| **Prometheus** | http://localhost:9090 | — |
| **Alertmanager** | http://localhost:9093 | — |
| **Loki** | http://localhost:3100 | — |

---

## 📊 O que está a ser monitorizado

### SLIs e SLOs

| SLI | SLO | Alerta |
|-----|-----|--------|
| Disponibilidade | ≥ 99.5% requests não-5xx (24h) | `AppDown`, `HighErrorRate` |
| Latência p99 | < 500ms (janela 5m) | `HighLatencyP99` |
| Taxa de erro | < 1% (janela 5m) | `HighErrorRate`, `CriticalErrorRate` |
| Error budget | Burn rate < 1x SLO | `ErrorBudgetBurnRateHigh` |

### Endpoints da aplicação

| Endpoint | Método | Comportamento | Propósito |
|----------|--------|---------------|-----------|
| `/health` | GET | Resposta imediata | Liveness probe |
| `/ready` | GET | Verifica dependências | Readiness probe |
| `/metrics` | GET | Formato Prometheus | Scraping endpoint |
| `/api/products` | GET | Latência 10–80ms | Endpoint rápido |
| `/api/orders` | GET | Latência 50–600ms | Pode disparar alerta de latência |
| `/api/process` | POST | Latência 100–900ms, 10% erros | Testa error rate SLO |
| `/api/slow` | GET | Latência 600ms–1.2s | **Sempre** dispara alerta de latência |
| `/api/error` | GET | Sempre 500 | Testa error alerts |

### Métricas Prometheus expostas

```promql
# Rate — taxa de pedidos
http_requests_total{method, endpoint, status}

# Duration — histograma de latência
http_request_duration_seconds_bucket{method, endpoint, le}
http_request_duration_seconds_sum{method, endpoint}
http_request_duration_seconds_count{method, endpoint}

# Saturation — pedidos em curso
http_active_requests

# Errors — contador de erros
http_errors_total{endpoint, error_type}

# Business metrics
orders_processed_total
products_listed_total
```

---

## 🧪 Gerar tráfego para testar os dashboards

```bash
# Tráfego normal misto (corre 60 segundos)
for i in $(seq 1 60); do
  curl -s http://localhost:5000/api/products > /dev/null
  curl -s http://localhost:5000/api/orders > /dev/null
  curl -s -X POST http://localhost:5000/api/process > /dev/null
  sleep 1
done

# Forçar alerta de latência
curl http://localhost:5000/api/slow

# Forçar alerta de erro
curl http://localhost:5000/api/error

# Stress test com hey (instalar: go install github.com/rakyll/hey@latest)
hey -n 1000 -c 10 http://localhost:5000/api/products
```

---

## 🔔 Testar Alertas

### 1. Verificar regras no Prometheus

```
http://localhost:9090/alerts
```

### 2. Ver alertas no Alertmanager

```
http://localhost:9093
```

### 3. Ver notificações no webhook

```bash
docker compose logs webhook-receiver -f
```

### 4. Forçar alerta `AppDown`

```bash
# Parar a aplicação
docker compose stop flask-app

# Aguardar ~1 min e verificar o Alertmanager
# Depois repor
docker compose start flask-app
```

---

## 🗂️ Estrutura do Projecto

```
.
├── app/
│   ├── main.py              # Flask app com endpoints e middleware
│   └── metrics.py           # Definições das métricas Prometheus
├── tests/
│   └── test_app.py          # Testes unitários (pytest)
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml   # Config de scraping e targets
│   │   └── alert.rules.yml  # Regras de alerta (SLO-based)
│   ├── grafana/
│   │   ├── provisioning/    # Auto-provisioning (zero config manual)
│   │   └── dashboards/      # Dashboard JSON (versionado em código)
│   ├── loki/
│   │   └── loki-config.yml  # Config de retenção e storage
│   ├── promtail/
│   │   └── promtail-config.yml  # Pipeline de processamento de logs
│   └── alertmanager/
│       └── alertmanager.yml # Routing, grouping, receivers
├── .github/workflows/
│   └── ci.yml               # Pipeline CI/CD completo
├── Dockerfile               # Multi-stage build, non-root user
├── docker-compose.yml       # Orquestração da stack completa
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔐 Boas Práticas Implementadas

### Segurança

- **Utilizador não-root** na imagem Docker (uid 1001)
- **Multi-stage build** — imagem final sem ferramentas de build
- **Credenciais via variáveis de ambiente** — nunca hardcoded
- **`.env` no `.gitignore`** — segredos não entram no repositório

### Observabilidade

- **Métricas RED** — Rate, Errors, Duration por endpoint
- **Alertas baseados em sintomas** — não em causas (Google SRE Book)
- **Error budget tracking** — para conversas de SLO com produto
- **Retention explícita** — Prometheus 30d, Loki 7d

### Operacional

- **Health checks** em todos os containers do Compose
- **`depends_on` com condição `service_healthy`** — ordem de arranque garantida
- **Dashboards como código** — versionados, reproduzíveis, sem config manual
- **Pipeline CI/CD** — valida configs Prometheus, Loki, Docker Compose

---

## 🛠️ Comandos Úteis

```bash
# Ver logs de todos os serviços
docker compose logs -f

# Ver apenas logs da app
docker compose logs flask-app -f

# Recarregar config do Prometheus sem restart
curl -X POST http://localhost:9090/-/reload

# Ver targets do Prometheus
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'

# Query PromQL manual
curl "http://localhost:9090/api/v1/query?query=http_requests_total" | jq .

# Ver métricas da app directamente
curl http://localhost:5000/metrics

# Parar e limpar tudo (incluindo volumes)
docker compose down -v --remove-orphans
```

---

## 🔬 Queries PromQL Úteis

```promql
# Taxa de pedidos por segundo (últimos 5min)
sum(rate(http_requests_total{job="flask-app"}[5m]))

# Taxa de erro (%)
sum(rate(http_requests_total{job="flask-app",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="flask-app"}[5m]))

# Latência p99 por endpoint
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{job="flask-app"}[5m]))
  by (le, endpoint)
)

# Error budget burn rate vs SLO de 99.5%
(
  sum(rate(http_requests_total{job="flask-app",status=~"5.."}[1h]))
  / sum(rate(http_requests_total{job="flask-app"}[1h]))
) / (1 - 0.995)
```

---

## 💡 Decisões de Arquitectura

**Por que Loki em vez de Elasticsearch?**
Loki usa um modelo de armazenamento baseado em labels (como Prometheus), o que reduz drasticamente o custo de ingestão. Para logs de aplicação onde precisamos de filtrar por serviço e nível, é mais que suficiente e é ordens de magnitude mais barato a operar.

**Por que alertas baseados em SLO em vez de thresholds?**
Alertas baseados em CPU ou memória são ruído — não sabemos se o utilizador está a ser afectado. Alertas baseados em taxa de erro e latência respondem directamente à pergunta "o utilizador está a ter uma má experiência?", que é o que importa em produção.

**Por que Promtail em vez de Fluentd/Filebeat?**
Promtail é o agente nativo do ecossistema Loki, tem configuração mais simples e integração directa com Docker. Para stacks Grafana, reduz a complexidade operacional.

---

## 📚 Referências

- [Google SRE Book — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [RED Method — Tom Wilkie](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/)

---

## 🤝 Contribuições

PRs são bem-vindas. Para mudanças significativas, abrir uma issue primeiro para discussão.

---

*Desenvolvido como projecto de portfolio demonstrando práticas SRE — não apenas "a app funciona" mas "eu sei quando está a falhar e porquê".*

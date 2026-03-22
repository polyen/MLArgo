# MLOps Experiments — Lesson 8-9

MLflow + MinIO + PostgreSQL + PushGateway + Prometheus + Grafana, розгорнуті через ArgoCD.

---

## Структура проєкту

```
MLArgo/
├── argo-cd/
│   └── applications/
│       ├── minio.yaml            # S3-сумісне сховище артефактів (official MinIO chart)
│       ├── postgres.yaml         # PostgreSQL (raw K8s manifests, postgres:17)
│       ├── mlflow.yaml           # MLflow Tracking Server
│       ├── pushgateway.yaml      # Prometheus PushGateway
│       ├── prometheus.yaml       # Prometheus Server (scrapes PushGateway)
│       └── grafana.yaml          # Grafana дашборд
├── k8s/
│   └── postgres/
│       ├── deployment.yaml       # PostgreSQL Deployment
│       └── service.yaml          # PostgreSQL Service
├── experiments/
│   ├── train_and_push.py         # Скрипт тренування
│   ├── requirements.txt
│   ├── .env                      # Локальні env vars (не в git)
│   └── .env.example              # Шаблон env vars
├── best_model/                   # З'являється після запуску скрипту
└── README.md
```

---

## 1. Розгортання інфраструктури через ArgoCD

Застосуйте всі Application-маніфести:

```bash
kubectl apply -f argo-cd/applications/minio.yaml
kubectl apply -f argo-cd/applications/postgres.yaml
kubectl apply -f argo-cd/applications/mlflow.yaml
kubectl apply -f argo-cd/applications/pushgateway.yaml
kubectl apply -f argo-cd/applications/prometheus.yaml
kubectl apply -f argo-cd/applications/grafana.yaml
```

---

## 2. Перевірка наявності MLflow і PushGateway у кластері

```bash
# Всі ArgoCD Applications
kubectl get applications -n argocd

# Поди в namespace application (MLflow, MinIO, PostgreSQL)
kubectl get pods -n application

# Поди в namespace monitoring (Prometheus, PushGateway, Grafana)
kubectl get pods -n monitoring
```

Очікуваний стан — всі поди `Running`, всі Applications у стані `Synced / Healthy`.

---

## 3. Port-forward

Відкрий окремий термінал для кожного сервісу:

```bash
# MLflow UI — http://localhost:5000
kubectl port-forward svc/mlflow 5000:5000 -n application

# MinIO S3 API — http://localhost:9000
kubectl port-forward svc/minio 9000:9000 -n application

# MinIO Console — http://localhost:9001
kubectl port-forward svc/minio-console 9001:9001 -n application

# PushGateway — http://localhost:9091
kubectl port-forward svc/prometheus-pushgateway 9091:9091 -n monitoring

# Prometheus — http://localhost:9090
kubectl port-forward svc/prometheus-server 9090:80 -n monitoring

# Grafana — http://localhost:3000
kubectl port-forward svc/grafana 3000:3000 -n monitoring
```

| Сервіс | URL | Логін |
|--------|-----|-------|
| MLflow UI | http://localhost:5000 | — |
| MinIO Console | http://localhost:9001 | `minio` / `minio123` |
| Grafana | http://localhost:3000 | `admin` / `admin123` |

---

## 4. Запуск train_and_push.py

### Встановлення залежностей

```bash
cd experiments
pip install -r requirements.txt
```

### Налаштування середовища

Скопіюй шаблон і за потреби відредагуй:

```bash
cp experiments/.env.example experiments/.env
```

Вміст `.env`:

```env
MLFLOW_TRACKING_URI=http://localhost:5000
PUSHGATEWAY_URL=localhost:9091
MLFLOW_S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minio
AWS_SECRET_ACCESS_KEY=minio123
```

### Запуск

> Перед запуском переконайся, що активні port-forward для MLflow, MinIO (9000) і PushGateway.

```bash
cd experiments
set -a && source .env && set +a
python train_and_push.py
```

Скрипт:
1. Тренує 9 моделей `SGDClassifier` на датасеті Iris (3 learning rate × 3 epochs).
2. Логує параметри, метрики та модель у MLflow.
3. Пушить `mlflow_accuracy` та `mlflow_loss` у PushGateway з міткою `run_id`.
4. Знаходить найкращу модель за accuracy.
5. Зберігає її у `best_model/` в корені проєкту.

Очікуваний вивід:

```
run_id=abc123  lr=0.001  epochs=50   acc=0.8000  loss=0.5202
run_id=def456  lr=0.01   epochs=50   acc=1.0000  loss=0.3247
...
Best run: def456  accuracy=1.0000
Best model saved to ./best_model/
```

---

## 5. Перегляд метрик у Grafana

1. Запусти port-forward для Grafana (порт 3000).
2. Відкрити: [http://localhost:3000](http://localhost:3000) — логін `admin` / `admin123`.
3. Перейти до **Explore** → обрати datasource **Prometheus**.
4. Виконати запити:

```promql
mlflow_accuracy
mlflow_loss
```

Для порівняння всіх запусків:

```promql
mlflow_accuracy{job="mlflow_training"}
mlflow_loss{job="mlflow_training"}
```

---

## 6. Змінні середовища

| Змінна | Значення за замовчуванням | Опис |
|--------|--------------------------|------|
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | URL MLflow Tracking Server |
| `PUSHGATEWAY_URL` | `localhost:9091` | Адреса Prometheus PushGateway |
| `MLFLOW_S3_ENDPOINT_URL` | `http://localhost:9000` | MinIO S3 endpoint |
| `AWS_ACCESS_KEY_ID` | `minio` | MinIO access key |
| `AWS_SECRET_ACCESS_KEY` | `minio123` | MinIO secret key |

---

## Скриншоти

<!-- Додайте скриншоти після запуску -->
- `screenshots/mlflow-ui.png` — MLflow UI з переліком runs
- `screenshots/grafana-explore.png` — Grafana Explore з метриками accuracy/loss

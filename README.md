# MLOps Experiments — Lesson 8-9

MLflow + MinIO + PostgreSQL + PushGateway + Prometheus + Grafana, розгорнуті через ArgoCD.

---

## Структура проєкту

```
MLArgo/
├── argo-cd/
│   └── applications/
│       ├── minio.yaml          # S3-сумісне сховище артефактів
│       ├── postgres.yaml       # PostgreSQL база для MLflow
│       ├── mlflow.yaml         # MLflow Tracking Server
│       ├── pushgateway.yaml    # Prometheus PushGateway
│       ├── prometheus.yaml     # Prometheus Server (скрейпить PushGateway)
│       └── grafana.yaml        # Grafana дашборд
├── experiments/
│   ├── train_and_push.py       # Скрипт тренування
│   └── requirements.txt
├── best_model/                 # З'явиться після запуску скрипту
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
# Переглянути всі ArgoCD Applications
kubectl get applications -n argocd

# Переглянути поди в namespace application
kubectl get pods -n application

# Переглянути поди в namespace monitoring
kubectl get pods -n monitoring

# Перевірити сервіси
kubectl get svc -n application
kubectl get svc -n monitoring
```

Очікуваний стан — всі поди `Running`, всі Applications у стані `Synced / Healthy`.

---

## 3. Port-forward

### MLflow UI (порт 5000)

```bash
kubectl port-forward svc/mlflow 5000:5000 -n application
```

Відкрити: [http://localhost:5000](http://localhost:5000)

### MinIO Console (порт 9001)

```bash
kubectl port-forward svc/minio 9001:9001 -n application
```

Відкрити: [http://localhost:9001](http://localhost:9001)
Логін: `minio` / `minio123`

### PushGateway (порт 9091)

```bash
kubectl port-forward svc/prometheus-pushgateway 9091:9091 -n monitoring
```

Відкрити: [http://localhost:9091](http://localhost:9091)

### Prometheus (порт 9090)

```bash
kubectl port-forward svc/prometheus-server 9090:80 -n monitoring
```

Відкрити: [http://localhost:9090](http://localhost:9090)

### Grafana (порт 3000)

```bash
kubectl port-forward svc/grafana 3000:3000 -n monitoring
```

Відкрити: [http://localhost:3000](http://localhost:3000)
Логін: `admin` / `admin123`

---

## 4. Запуск train_and_push.py

### Встановлення залежностей

```bash
cd experiments
pip install -r requirements.txt
```

### Запуск (потрібен активний port-forward для MLflow і PushGateway)

```bash
# Термінал 1
kubectl port-forward svc/mlflow 5000:5000 -n application

# Термінал 2
kubectl port-forward svc/prometheus-pushgateway 9091:9091 -n monitoring

# Термінал 3
cd experiments
MLFLOW_TRACKING_URI=http://localhost:5000 \
PUSHGATEWAY_URL=localhost:9091 \
python train_and_push.py
```

Скрипт:
1. Тренує 9 моделей `SGDClassifier` на датасеті Iris (3 learning rate × 3 epoch).
2. Логує параметри, метрики та модель у MLflow.
3. Пушить `mlflow_accuracy` та `mlflow_loss` у PushGateway з міткою `run_id`.
4. Знаходить найкращу модель за accuracy.
5. Зберігає її у директорію `best_model/` в корені проєкту.

Очікуваний вивід:

```
run_id=abc123  lr=0.001  epochs=50   acc=0.9333  loss=0.2145
run_id=def456  lr=0.001  epochs=100  acc=0.9667  loss=0.1823
...
Best run: def456  accuracy=0.9667
Best model saved to ./best_model/
```

---

## 5. Перегляд метрик у Grafana

1. Відкрити Grafana: [http://localhost:3000](http://localhost:3000)
2. Перейти до **Explore** (іконка компасу в лівому меню).
3. Обрати datasource **Prometheus**.
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

| Змінна | За замовчуванням | Опис |
|--------|-----------------|------|
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | URL MLflow Tracking Server |
| `PUSHGATEWAY_URL` | `localhost:9091` | Адреса Prometheus PushGateway |

---

## Скриншоти

<!-- Додайте скриншоти після запуску -->
- `screenshots/mlflow-ui.png` — MLflow UI з переліком runs
- `screenshots/grafana-explore.png` — Grafana Explore з метриками accuracy/loss

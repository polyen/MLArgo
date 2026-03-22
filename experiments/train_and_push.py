import os
import shutil
import mlflow
import mlflow.sklearn
from sklearn.datasets import load_iris
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
PUSHGATEWAY_URL     = os.getenv("PUSHGATEWAY_URL",     "localhost:9091")
EXPERIMENT_NAME     = "iris-sgd-sweep"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment(EXPERIMENT_NAME)

# Dataset
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42
)

# Hyperparameter grid
param_grid = [
    {"learning_rate": lr, "max_iter": epochs}
    for lr in [0.001, 0.01, 0.1]
    for epochs in [50, 100, 200]
]

best_accuracy = -1.0
best_run_id   = None

#Training loop
for params in param_grid:
    with mlflow.start_run() as run:
        run_id = run.info.run_id

        model = SGDClassifier(
            eta0=params["learning_rate"],
            max_iter=params["max_iter"],
            loss="log_loss",
            learning_rate="constant",
            random_state=42,
        )
        model.fit(X_train, y_train)

        y_pred  = model.predict(X_test)
        y_prob  = model.predict_proba(X_test)
        acc     = accuracy_score(y_test, y_pred)
        loss    = log_loss(y_test, y_prob)

        # Log to MLflow
        mlflow.log_params(params)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("loss",     loss)
        mlflow.sklearn.log_model(model, artifact_path="model")

        print(f"run_id={run_id}  lr={params['learning_rate']}  "
              f"epochs={params['max_iter']}  acc={acc:.4f}  loss={loss:.4f}")

        #Push metrics to PushGateway
        registry = CollectorRegistry()
        g_acc  = Gauge("mlflow_accuracy", "MLflow run accuracy",
                       ["run_id"], registry=registry)
        g_loss = Gauge("mlflow_loss",     "MLflow run loss",
                       ["run_id"], registry=registry)
        g_acc.labels(run_id=run_id).set(acc)
        g_loss.labels(run_id=run_id).set(loss)

        push_to_gateway(
            PUSHGATEWAY_URL,
            job="mlflow_training",
            grouping_key={"run_id": run_id},
            registry=registry,
        )

        if acc > best_accuracy:
            best_accuracy = acc
            best_run_id   = run_id

print(f"\nBest run: {best_run_id}  accuracy={best_accuracy:.4f}")

best_model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "best_model")
if os.path.exists(best_model_dir):
    shutil.rmtree(best_model_dir)

best_model_uri = f"runs:/{best_run_id}/model"
mlflow.artifacts.download_artifacts(
    artifact_uri=best_model_uri,
    dst_path=best_model_dir,
)
print(f"Best model saved to ./{best_model_dir}/")


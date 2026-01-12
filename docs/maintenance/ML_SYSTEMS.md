# Machine Learning Systems Maintenance

This document describes the maintenance and operations of the AI/ML components in Sensei OS.

## ML Architecture Overview

Sensei OS uses a hybrid ML architecture:
- **Local-First Inference**: ONNX models run directly on the application servers or edge devices for low-latency tasks (e.g., visual quality inspection, text embeddings).
- **Asynchronous Training/Heavy Inference**: Heavy ML tasks are offloaded to Celery workers to avoid blocking the API thread.

## ML Pipeline

The `EnhancedMLPipelineService` manages the lifecycle of models:
1. **Data Preparation**: Extraction and cleaning of features from the PostgreSQL database.
2. **Training**: Model training using PyTorch or scikit-learn.
3. **Evaluation**: Validation against a test set with performance metrics.
4. **Export**: Exporting trained models to ONNX format for efficient inference.
5. **Deployment**: Uploading model weights to S3 and notifying services to reload.

## Asynchronous Offloading

All `train()` and heavy `predict()` methods must be offloaded to Celery.
Example:
```python
# In the API endpoint
from sensei.worker.tasks import train_model_task
train_model_task.delay(model_id="cbm_predictor")
```

## Model Retraining

Models should be retrained periodically as new data becomes available.
- **Trigger-based**: Retrain when data drift is detected or when a significant amount of new data is collected.
- **Schedule-based**: Monthly or quarterly retraining for stable models.

## Monitoring Model Health

Monitor the following metrics in the **Advanced Analytics** dashboard:
- **Inference Latency**: Time taken for model predictions.
- **Accuracy/F1-Score**: Real-world performance against actual outcomes (e.g., predicted vs. actual equipment failure).
- **Resource Usage**: CPU/GPU and Memory consumption of ML workers.

## Troubleshooting

- **Worker OOM**: If workers crash during training, increase the memory limit in the Helm chart for the `worker` deployment.
- **Stale Predictions**: Ensure the Celery worker has access to the latest model weights in S3 and that the cache invalidation is working.
- **ONNX Incompatibility**: Ensure the opset version used during export matches the version supported by the `onnxruntime` installed in the container.

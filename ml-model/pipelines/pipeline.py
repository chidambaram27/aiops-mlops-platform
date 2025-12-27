# ml-model/pipelines/pipeline.py
"""
Kubeflow Pipeline for Anomaly Detection - Single File Approach
"""
import kfp
from kfp import dsl
from kfp.dsl import (
    Input,
    Output,
    Dataset,
    Model,
    Metrics,
    component
)

@component(
    base_image='python:3.13-slim',
    packages_to_install=['pandas==2.3.3', 'prometheus-api-client==0.7.0', 'requests==2.31.0']
)
def fetch_data_component(
    prometheus_url: str,
    training_hours: int,
    instance_ip: str,
    output_data: Output[Dataset]
):
    """Fetch CPU metrics from Prometheus"""
    import os
    import pandas as pd
    from datetime import datetime, timedelta
    from prometheus_api_client import PrometheusConnect
    
    prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
    prom.check_prometheus_connection()
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=training_hours)
    metrics_query = f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle", instance="{instance_ip}"}}[5m])) * 100)'
    
    result = prom.custom_query_range(
        query=metrics_query,
        start_time=start_time,
        end_time=end_time,
        step='10s'
    )
    
    if not result:
        raise ValueError("No data returned from Prometheus")
    
    timestamps = []
    values = []
    for sample in result[0]['values']:
        timestamps.append(datetime.fromtimestamp(sample[0]).isoformat())
        values.append(float(sample[1]))
    
    df = pd.DataFrame({'timestamp': timestamps, 'cpu_usage': values})
    df.to_csv(output_data.path, index=False)
    print(f"✓ Fetched {len(df)} data points")

@component(
    base_image='python:3.13-slim',
    packages_to_install=['pandas==2.3.3']
)
def engineer_features_component(
    input_data: Input[Dataset],
    output_features: Output[Dataset]
):
    """Engineer features for ML"""
    import pandas as pd
    
    df = pd.read_csv(input_data.path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    df['rolling_mean'] = df['cpu_usage'].rolling(window=5, min_periods=1).mean()
    df['rolling_std'] = df['cpu_usage'].rolling(window=5, min_periods=1).std().fillna(0)
    df['rate_of_change'] = df['cpu_usage'].diff().fillna(0)
    df['hour'] = df['timestamp'].dt.hour
    df = df.dropna()
    
    df.to_csv(output_features.path, index=False)
    print(f"✓ Created features for {len(df)} samples")

@component(
    base_image='python:3.13-slim',
    packages_to_install=['pandas==2.3.3', 'numpy==2.3.5', 'scikit-learn==1.8.0']
)
def train_model_component(
    input_features: Input[Dataset],
    output_model: Output[Model],
    output_metrics: Output[Metrics],
    contamination: float = 0.05,
    n_estimators: int = 100
):
    """Train IsolationForest model"""
    import pickle
    import json
    import pandas as pd
    import os
    from sklearn.ensemble import IsolationForest
    
    df = pd.read_csv(input_features.path)
    feature_columns = ['cpu_usage', 'rolling_mean', 'rolling_std', 'rate_of_change', 'hour']
    X = df[feature_columns]
    
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=n_estimators
    )
    model.fit(X)
    
    predictions = model.predict(X)
    anomalies = (predictions == -1).sum()
    normal = (predictions == 1).sum()
    
    # Save model
    os.makedirs(output_model.path, exist_ok=True)
    with open(f"{output_model.path}/model.pkl", 'wb') as f:
        pickle.dump(model, f)
    
    # Save metrics
    metrics = {
        'training_samples': len(X),
        'normal_samples': int(normal),
        'anomalies_detected': int(anomalies),
        'normal_percentage': float(normal / len(X) * 100),
        'anomalies_percentage': float(anomalies / len(X) * 100)
    }
    
    with open(output_metrics.path, 'w') as f:
        json.dump(metrics, f)
    
    print(f"✓ Model trained: {normal} normal, {anomalies} anomalies")

@component(
    base_image='python:3.13-slim',
    packages_to_install=['kubernetes==30.1.0', 'pyyaml==6.0.2']
)
def deploy_inference_component(
    input_model: Input[Model],
    inference_service_name: str = "sklearn-iris",
    namespace: str = "default",
    service_account_name: str = "sa-minio-kserve",
    storage_uri_override: str = ""  # Optional: override if auto-detection fails
):
    """Deploy InferenceService to cluster using model artifact location"""
    import os
    import yaml
    import json
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    
    # Load in-cluster config (Kubeflow pipelines run in-cluster)
    try:
        config.load_incluster_config()
    except:
        # Fallback to kubeconfig if not in-cluster
        config.load_kube_config()
    
    # Get the storage URI from the model artifact
    # In Kubeflow Pipelines v2, artifacts have metadata files with URI information
    model_path = input_model.path
    storage_uri = storage_uri_override.strip() if storage_uri_override else None
    
    if not storage_uri:
        # Method 1: Try to read from metadata.json (KFP v2 artifact metadata)
        # Check multiple possible locations for metadata
        metadata_paths = [
            os.path.join(model_path, "metadata.json"),
            os.path.join(model_path, "..", "metadata.json"),
            os.path.join(os.path.dirname(model_path), "metadata.json"),
        ]
        
        for metadata_path in metadata_paths:
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        # Try different metadata structures
                        if "outputs" in metadata and "artifacts" in metadata["outputs"]:
                            artifacts = metadata["outputs"]["artifacts"]
                            if artifacts and len(artifacts) > 0:
                                storage_uri = artifacts[0].get("uri", "")
                        elif "uri" in metadata:
                            storage_uri = metadata["uri"]
                        elif "metadata" in metadata and "uri" in metadata["metadata"]:
                            storage_uri = metadata["metadata"]["uri"]
                        
                        if storage_uri:
                            break
                except Exception as e:
                    print(f"Warning: Could not read {metadata_path}: {e}")
                    continue
    
    # Method 2: Try to get from KFP environment variables
    # In Kubeflow, the artifact URI might be available via environment
    if not storage_uri:
        # Check for KFP-specific environment variables
        kfp_uri = os.environ.get("KFP_ARTIFACT_URI") or os.environ.get("ARTIFACT_URI")
        if kfp_uri:
            storage_uri = kfp_uri
    
    # Method 3: Try to construct from model path and known patterns
    # This is a fallback - the path structure in KFP can vary
    if not storage_uri:
        artifact_base = os.environ.get("ARTIFACT_STORE", "s3://mlpipeline/v2")
        # Try to extract information from the path
        # Model paths in KFP often contain run/execution IDs
        path_parts = model_path.split("/")
        
        # Look for patterns like: .../artifacts/pipeline-name/run-id/component/output
        try:
            artifacts_idx = next(i for i, part in enumerate(path_parts) if part == "artifacts")
            if artifacts_idx and artifacts_idx + 3 < len(path_parts):
                # Reconstruct S3 path from local path structure
                relative_path = "/".join(path_parts[artifacts_idx:])
                storage_uri = f"{artifact_base}/{relative_path}"
        except (StopIteration, ValueError):
            pass
    
    # Final validation
    if not storage_uri:
        raise ValueError(
            f"Could not extract S3 URI from model artifact. "
            f"Model path: {model_path}. "
            f"Please provide storage_uri_override parameter or ensure artifact metadata is available."
        )
    
    # Ensure we have a valid S3 URI
    if not storage_uri.startswith("s3://"):
        # If it's a relative path, prepend the artifact store
        if not storage_uri.startswith("/"):
            artifact_base = os.environ.get("ARTIFACT_STORE", "s3://mlpipeline/v2")
            storage_uri = f"{artifact_base}/{storage_uri.lstrip('/')}"
        else:
            raise ValueError(f"Invalid storage URI format: {storage_uri}. Expected S3 URI starting with 's3://'")
    
    print(f"Deploying InferenceService with storageUri: {storage_uri}")
    
    # Create InferenceService manifest
    inference_service = {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": inference_service_name,
            "namespace": namespace,
            "annotations": {
                "alb.ingress.kubernetes.io/scheme": "internet-facing",
                "alb.ingress.kubernetes.io/target-type": "ip"
            }
        },
        "spec": {
            "predictor": {
                "serviceAccountName": service_account_name,
                "model": {
                    "modelFormat": {
                        "name": "sklearn"
                    },
                    "protocolVersion": "v2",
                    "runtime": "kserve-sklearnserver",
                    "storageUri": storage_uri
                }
            }
        }
    }
    
    # Apply InferenceService using Kubernetes API
    api_instance = client.CustomObjectsApi()
    group = "serving.kserve.io"
    version = "v1beta1"
    plural = "inferenceservices"
    
    try:
        # Check if InferenceService already exists
        try:
            existing = api_instance.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=inference_service_name
            )
            print(f"InferenceService {inference_service_name} already exists. Updating...")
            # Update existing
            api_instance.patch_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=inference_service_name,
                body=inference_service
            )
            print(f"✓ InferenceService {inference_service_name} updated successfully")
        except ApiException as e:
            if e.status == 404:
                # Create new InferenceService
                api_instance.create_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural,
                    body=inference_service
                )
                print(f"✓ InferenceService {inference_service_name} created successfully")
            else:
                raise
    
    except ApiException as e:
        print(f"Error deploying InferenceService: {e}")
        print(f"Response body: {e.body}")
        raise
    
    print(f"✓ InferenceService deployed: {inference_service_name}")
    print(f"  Storage URI: {storage_uri}")
    print(f"  Namespace: {namespace}")

@dsl.pipeline(
    name='anomaly-detection-training',
    description='Train anomaly detection model from Prometheus metrics'
)
def anomaly_detection_pipeline(
    prometheus_url: str = "http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090",
    training_hours: int = 2,
    instance_ip: str = "10.0.0.194:9100",
    contamination: float = 0.05,
    n_estimators: int = 100
):
    """Main pipeline definition"""
    
    # Step 1: Fetch data
    fetch_task = fetch_data_component(
        prometheus_url=prometheus_url,
        training_hours=training_hours,
        instance_ip=instance_ip
    )
    
    # Step 2: Engineer features
    engineer_task = engineer_features_component(
        input_data=fetch_task.outputs['output_data']
    )
    
    # Step 3: Train model
    train_task = train_model_component(
        input_features=engineer_task.outputs['output_features'],
        contamination=contamination,
        n_estimators=n_estimators
    )
    
    # Step 4: Deploy InferenceService
    deploy_task = deploy_inference_component(
        input_model=train_task.outputs['output_model'],
        inference_service_name="anomaly-detection",
        namespace="default",
        service_account_name="sa-minio-kserve"
    )

if __name__ == "__main__":
    kfp.compiler.Compiler().compile(
        pipeline_func=anomaly_detection_pipeline,
        package_path='generated-anomaly-detection-pipeline.yaml'
    )
    print("✓ Pipeline compiled to generated-anomaly-detection-pipeline.yaml")
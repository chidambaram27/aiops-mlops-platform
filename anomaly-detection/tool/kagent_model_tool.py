# kagent/model_tool/kagent_model_tool.py
"""
FastMCP Server for Anomaly Detection Model Predictions
Integrates Prometheus MCP with KServe InferenceService
Uses HTTP transport for MCP communication
"""
import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from prometheus_api_client import PrometheusConnect
from fastmcp import FastMCP


class AnomalyDetectionTool:
    """Tool for querying Prometheus and getting model predictions"""
    
    def __init__(
        self,
        prometheus_url: str,
        inference_service_url: str,
        model_name: str = "sklearn-iris",
        namespace: str = "default"
    ):
        """
        Initialize the tool
        
        Args:
            prometheus_url: Prometheus service URL
            inference_service_url: KServe InferenceService URL (can be internal or external)
            model_name: Name of the InferenceService
            namespace: Kubernetes namespace
        """
        self.prometheus_url = prometheus_url
        self.inference_service_url = inference_service_url
        self.model_name = model_name
        self.namespace = namespace
        self.prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
        
    def query_prometheus(
        self,
        query: str,
        hours: int = 1,
        step: str = "10s"
    ) -> pd.DataFrame:
        """
        Query Prometheus for metrics
        
        Args:
            query: PromQL query
            hours: Number of hours of data to fetch
            step: Query resolution step
            
        Returns:
            DataFrame with timestamp and value columns
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        result = self.prom.custom_query_range(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step=step
        )
        
        if not result:
            raise ValueError("No data returned from Prometheus")
        
        timestamps = []
        values = []
        for sample in result[0]['values']:
            timestamps.append(datetime.fromtimestamp(sample[0]).isoformat())
            values.append(float(sample[1]))
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'cpu_usage': values
        })
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features matching the training pipeline
        
        Args:
            df: DataFrame with timestamp and cpu_usage columns
            
        Returns:
            DataFrame with engineered features
        """
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['rolling_mean'] = df['cpu_usage'].rolling(window=5, min_periods=1).mean()
        df['rolling_std'] = df['cpu_usage'].rolling(window=5, min_periods=1).std().fillna(0)
        df['rate_of_change'] = df['cpu_usage'].diff().fillna(0)
        df['hour'] = df['timestamp'].dt.hour
        df = df.dropna()
        
        return df
    
    def predict(
        self,
        features: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Call KServe InferenceService for predictions
        
        Args:
            features: List of feature vectors [cpu_usage, rolling_mean, rolling_std, rate_of_change, hour]
            
        Returns:
            Prediction results
        """
        # KServe v2 protocol format
        payload = {
            "inputs": [
                {
                    "name": "input-0",
                    "shape": [len(features), 5],
                    "datatype": "FP64",
                    "data": features
                }
            ]
        }
        
        # Construct endpoint URL
        # Internal: http://sklearn-iris.default.svc.cluster.local/v2/models/sklearn-iris/infer
        # External: Use the ALB URL if exposed
        endpoint = f"{self.inference_service_url}/v2/models/{self.model_name}/infer"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def predict_from_prometheus(
        self,
        query: str = '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        Complete workflow: Query Prometheus -> Engineer features -> Predict
        
        Args:
            query: PromQL query
            hours: Hours of data to analyze
            
        Returns:
            Dictionary with predictions, metadata, and anomaly timing information
        """
        # Step 1: Query Prometheus
        df = self.query_prometheus(query, hours=hours)
        
        # Step 2: Engineer features
        df_features = self.engineer_features(df)
        
        # Step 3: Prepare features for model
        feature_columns = ['cpu_usage', 'rolling_mean', 'rolling_std', 'rate_of_change', 'hour']
        features = df_features[feature_columns].values.tolist()
        
        # Step 4: Get predictions
        predictions = self.predict(features)
        
        # Step 5: Format results
        # KServe returns predictions in format: {"outputs": [{"name": "output-0", "data": [...]}]}
        prediction_values = predictions.get("outputs", [{}])[0].get("data", [])
        
        # IsolationForest returns -1 for anomalies, 1 for normal
        anomalies = sum(1 for p in prediction_values if p == -1)
        normal = sum(1 for p in prediction_values if p == 1)
        
        # Step 6: Extract anomaly timing information
        # Find all anomalies with their timestamps and CPU usage
        anomaly_details = []
        for i, pred in enumerate(prediction_values):
            if pred == -1:  # Anomaly detected
                timestamp = df_features['timestamp'].iloc[i]
                anomaly_details.append({
                    'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                    'cpu_usage': float(df_features['cpu_usage'].iloc[i]),
                    'index': i
                })
        
        # Find first anomaly time
        first_anomaly_time = anomaly_details[0]['timestamp'] if anomaly_details else None
        
        # Find anomaly periods (consecutive anomalies)
        # Step interval is 10s based on query_prometheus default
        step_seconds = 10
        anomaly_periods = []
        period_start_idx = None
        
        for i, pred in enumerate(prediction_values):
            if pred == -1:  # Anomaly
                if period_start_idx is None:
                    period_start_idx = i
            else:  # Normal
                if period_start_idx is not None:
                    # Period ended, record it
                    start_timestamp = df_features['timestamp'].iloc[period_start_idx]
                    end_timestamp = df_features['timestamp'].iloc[i - 1]
                    duration_seconds = (i - period_start_idx) * step_seconds
                    
                    anomaly_periods.append({
                        'start': start_timestamp.isoformat() if hasattr(start_timestamp, 'isoformat') else str(start_timestamp),
                        'end': end_timestamp.isoformat() if hasattr(end_timestamp, 'isoformat') else str(end_timestamp),
                        'duration_seconds': duration_seconds,
                        'duration_formatted': f"{duration_seconds // 60}m {duration_seconds % 60}s"
                    })
                    period_start_idx = None
        
        # Handle case where anomaly continues to the end of the data
        if period_start_idx is not None:
            start_timestamp = df_features['timestamp'].iloc[period_start_idx]
            end_timestamp = df_features['timestamp'].iloc[-1]
            duration_seconds = (len(prediction_values) - period_start_idx) * step_seconds
            
            anomaly_periods.append({
                'start': start_timestamp.isoformat() if hasattr(start_timestamp, 'isoformat') else str(start_timestamp),
                'end': end_timestamp.isoformat() if hasattr(end_timestamp, 'isoformat') else str(end_timestamp),
                'duration_seconds': duration_seconds,
                'duration_formatted': f"{duration_seconds // 60}m {duration_seconds % 60}s"
            })
        
        return {
            "total_samples": len(features),
            "anomalies_detected": anomalies,
            "normal_samples": normal,
            "anomaly_percentage": (anomalies / len(features) * 100) if features else 0,
            "predictions": prediction_values,
            "timestamps": [ts.isoformat() if hasattr(ts, 'isoformat') else str(ts) for ts in df_features['timestamp'].tolist()],
            "cpu_usage": df_features['cpu_usage'].tolist(),
            # Anomaly timing information
            "first_anomaly_time": first_anomaly_time,
            "anomaly_periods": anomaly_periods,
            "anomaly_details": anomaly_details
        }


# Configuration from environment
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://kube-prometheus-stack-prometheus.kube-prometheus-stack.svc.cluster.local:9090"
)
INFERENCE_SERVICE_URL = os.getenv(
    "INFERENCE_SERVICE_URL",
    "http://sklearn-iris.default.svc.cluster.local"
)
MODEL_NAME = os.getenv("MODEL_NAME", "sklearn-iris")
DEFAULT_INSTANCE_IP = os.getenv("DEFAULT_INSTANCE_IP", "10.0.1.10:9100")

# Initialize tool
tool = AnomalyDetectionTool(
    prometheus_url=PROMETHEUS_URL,
    inference_service_url=INFERENCE_SERVICE_URL,
    model_name=MODEL_NAME
)

# Initialize FastMCP Server
mcp = FastMCP("Anomaly Detection Model")


@mcp.tool()
def predict_anomalies(
    instance_ip: str = DEFAULT_INSTANCE_IP,
    hours: int = 1
) -> str:
    """
    Predict anomalies in cluster metrics by querying Prometheus and using the ML model.
    Queries Prometheus for CPU usage metrics, engineers features, and predicts anomalies.
    
    Args:
        instance_ip: Prometheus instance IP and port (e.g., "10.0.0.194:9100")
        hours: Number of hours of historical data to analyze (1-24)
    
    Returns:
        Formatted string with anomaly detection results including timing information
    """
    query = f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle", instance="{instance_ip}"}}[5m])) * 100)'
    try:
        # Validate hours
        if hours < 1 or hours > 24:
            return f"Error: hours must be between 1 and 24, got {hours}"
        
        result = tool.predict_from_prometheus(query=query, hours=hours)
        
        # Format response with timing information
        response_text = f"""Anomaly Detection Results:

Total Samples Analyzed: {result['total_samples']}
Anomalies Detected: {result['anomalies_detected']}
Normal Samples: {result['normal_samples']}
Anomaly Percentage: {result['anomaly_percentage']:.2f}%

"""
        
        # Add timing information if anomalies were detected
        if result['anomalies_detected'] > 0:
            response_text += f"⏰ First Anomaly Detected: {result['first_anomaly_time']}\n\n"
            
            if result['anomaly_periods']:
                response_text += "Anomaly Periods:\n"
                for i, period in enumerate(result['anomaly_periods'], 1):
                    response_text += f"  Period {i}:\n"
                    response_text += f"    Start: {period['start']}\n"
                    response_text += f"    End: {period['end']}\n"
                    response_text += f"    Duration: {period['duration_formatted']}\n"
                response_text += "\n"
        else:
            response_text += "✓ No anomalies detected in the analyzed time period.\n\n"
        
        response_text += f"""Details:
- The model analyzed {result['total_samples']} data points
- {result['anomalies_detected']} anomalies were detected (marked as -1)
- {result['normal_samples']} samples were classified as normal (marked as 1)
- Anomaly rate: {result['anomaly_percentage']:.2f}%

This indicates potential issues in the cluster metrics that may require attention.
"""
        return response_text
    
    except Exception as e:
        return f"Error predicting anomalies: {str(e)}"


@mcp.tool()
def query_prometheus_and_predict(
    instance_ip: str = DEFAULT_INSTANCE_IP,
    time_range_hours: int = 1
) -> str:
    """
    Query Prometheus metrics and get anomaly predictions.
    This tool fetches metrics from Prometheus, engineers features, and returns model predictions.
    
    Args:
        instance_ip: Prometheus instance IP and port (e.g., "10.0.0.194:9100")
        time_range_hours: Time range in hours to query (default: 1)
    
    Returns:
        Formatted string with prediction results including timing information
    """
    promql_query = f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle", instance="{instance_ip}"}}[5m])) * 100)'
    try:
        if not promql_query:
            return "Error: promql_query parameter is required"
        
        if time_range_hours < 1 or time_range_hours > 24:
            return f"Error: time_range_hours must be between 1 and 24, got {time_range_hours}"
        
        result = tool.predict_from_prometheus(query=promql_query, hours=time_range_hours)
        
        response_text = f"""Query: {promql_query}
Time Range: {time_range_hours} hours

Results:
- Total Samples: {result['total_samples']}
- Anomalies: {result['anomalies_detected']} ({result['anomaly_percentage']:.2f}%)
- Normal: {result['normal_samples']}

"""
        
        # Add timing information if anomalies were detected
        if result['anomalies_detected'] > 0:
            response_text += f"⏰ First Anomaly: {result['first_anomaly_time']}\n"
            
            if result['anomaly_periods']:
                response_text += f"\nAnomaly Periods ({len(result['anomaly_periods'])}):\n"
                for i, period in enumerate(result['anomaly_periods'], 1):
                    response_text += f"  {i}. {period['start']} → {period['end']} ({period['duration_formatted']})\n"
        else:
            response_text += "✓ No anomalies detected.\n"
        
        response_text += "\nAnomaly predictions completed successfully."
        return response_text
    
    except Exception as e:
        return f"Error querying Prometheus and predicting: {str(e)}"


if __name__ == "__main__":
    # FastMCP will use HTTP transport if FASTMCP_TRANSPORT=http is set via environment variable
    # The server will be accessible at http://0.0.0.0:8080/mcp
    # Defaults to stdio if FASTMCP_TRANSPORT is not set
    mcp.run(transport="http")
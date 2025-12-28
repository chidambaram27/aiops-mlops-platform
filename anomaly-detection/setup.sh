#!/bin/sh

# to scale up the loadtest t3.small instance
kubectl apply dummy_pod.yaml

# update the DEFAULT_INSTANCE_IP set to the t3.small instance
docker buildx build --platform linux/amd64 -t chidambaram27/anomaly-detection-tool:v2 ./tool

docker push chidambaram27/anomaly-detection-tool:v1

# deploy model_tool as fastmcp server for KAgent
# update INFERENCE_SERVICE_URL, MODEL_NAME, DEFAULT_INSTANCE_IP
kubectl apply -f model_tool.yaml

# deploy KAgent RemoteMCPServer
kubectl apply -f mcpserver.yaml

# deploy Agent
kubectl apply -f agent.yaml
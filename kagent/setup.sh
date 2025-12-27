#!/bin/sh

# install crd
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
    --namespace kagent \
    --create-namespace

# free api key
export GEMINI_API_KEY=""

# install kagent resources
helm install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent 
    --namespace kagent \
    --set providers.default=gemini \
    --set providers.gemini.apiKey=$GEMINI_API_KEY \
    --set grafana-mcp.grafana.apiKey=$GRAFANA_API_KEY \
    -f ./kagent/helm-values.yaml


kubectl port-forward -n kagent svc/kagent-ui 8080:8080 > /dev/null 2>&1 & 

# ################################################################################
# #                            KAGENT DEPLOYED                                  #
# ################################################################################

# Kagent has been successfully deployed to namespace: kagent

# ACCESSING THE UI:
#   1. Forward the UI service port:
#      kubectl -n kagent port-forward service/kagent-ui 8080:8080

#   2. Open your browser and visit:
#      http://localhost:8080

# ACCESSING THE CONTROLLER API:
#   kubectl -n kagent port-forward service/kagent-controller 8083:8083
  
#   API endpoint: http://localhost:8083/api

# DEPLOYED COMPONENTS:
#   - Controller: kagent-controller (manages Kubernetes resources)
#   - Engine: kagent-engine (AI agent runtime)
#   - UI: kagent-ui (web interface)
#   - KMCP Controller: kagent-kmcp-manager-controller (manages MCPServer resources)

# ENABLED TOOLS:
#   - Tool Server: Kagent's Built-in tools
#   - grafana-mcp
#   - querydoc

# ENABLED AGENTS:
#   - k8s-agent
#   - kgateway-agent
#   - promql-agent

# USEFUL COMMANDS:
#   # View all kagent resources
#   kubectl -n kagent get agents,modelconfigs,toolservers,memories

#   # Get agents
#   kubectl -n kagent get agents

#   # View logs
#   kubectl -n kagent logs -l app.kubernetes.io/name=kagent -f

# TROUBLESHOOTING:
#   - Check pod status: kubectl -n kagent get pods
#   - View events: kubectl -n kagent get events --sort-by='.lastTimestamp'
#   - Controller logs: kubectl -n kagent logs -l app.kubernetes.io/component=controller -f

# DOCUMENTATION:
#   Visit https://kagent.dev for comprehensive documentation and examples.

# ################################################################################
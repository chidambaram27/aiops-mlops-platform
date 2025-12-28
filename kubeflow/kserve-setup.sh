#!/bin/sh

helm install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd --version v0.15.0

helm install kserve oci://ghcr.io/kserve/charts/kserve --version v0.15.0 \
  --set kserve.controller.deploymentMode=RawDeployment \
  --set kserve.controller.gateway.ingressGateway.className=alb \
  --namespace kubeflow
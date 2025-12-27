#!/bin/sh

# make gp2 as default storageClass
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}' 

# setup Kubeflow Pipeline Standalone
export PIPELINE_VERSION=2.14.0

kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io

# the default dev & platform agnostic will fail due to issues with cert managementm, in eks kubelet won't request the webhook-tls-certs
# so to avoid that need to go with cert-manager specific deployment method
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=$PIPELINE_VERSION"

# the default minio image would be wrong
kubectl set image deployment/minio minio=minio/minio:RELEASE.2025-09-07T16-13-09Z -n kubeflow 

# If you don't see the default example pipelines 
kubectl rollout restart -n kubeflow deploy ml-pipeline

# Need to troubleshoot why these two are failing 
# cache-server - due to webhook-tls-secret not found error
# cache-deployer-deployment - the csr approved cert not getting the certificate object
kubectl scale deploy -n kubeflow cache-server --replicas 0 
kubectl scale deploy -n kubeflow cache-deployer-deployment --replicas 0


# port-forward kubeflow pipeline UI - localhost:8000
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8000:80 > /dev/null 2>&1 & 

# port-forward 38969 minio UI - localhost:8001
# port 9000 -> API
# minio / minio123
kubectl port-forward -n kubeflow deploy/minio 8001:38969 > /dev/null 2>&1 &
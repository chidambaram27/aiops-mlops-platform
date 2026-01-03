#!/bin/sh

helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

# latest jaeger version doesn't have allInOne Mode, so use 4.1.5

helm upgrade --install jaeger jaegertracing/jaeger \
  --namespace jaeger \
  --create-namespace \
  --history-max 3 \
  --version 4.1.5 \
  --values helm-values.yaml

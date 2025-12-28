#!/bin/sh

python -m venv myenv

source myenv/bin/activate

pip install -r requirements.txt

python pipeline.py 

kubectl apply -f minio.yaml 
kubectl apply -f rbac.yaml

# manually upload the generated pipeline file to Kubeflow
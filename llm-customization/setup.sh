#!/bin/sh 

# dummy secret 
kubectl create secret generic kagent-my-provider -n kagent --from-literal PROVIDER_API_KEY=$PROVIDER_API_KEY


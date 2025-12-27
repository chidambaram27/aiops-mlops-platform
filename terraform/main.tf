/**
* # AIOps-MLOps-Platform
* 
* This Terraform configuration deploys a complete MLOps + AIOps platform infrastructure on AWS.
* The platform combines:
* - MLOps Component: Kubeflow for machine learning model development and deployment
*   to predict resource usage (CPU, memory, disk, network)
* - AIOps Component: LLM-powered interface for natural language queries and system interaction
*
* ## Infrastructure Components:
* - VPC: Virtual Private Cloud with public and private subnets across multiple availability zones
* - EKS: Amazon Elastic Kubernetes Service cluster for container orchestration
* - EKS Blueprints Addons: Essential Kubernetes addons including:
*   - AWS Load Balancer Controller
*   - Cert Manager
*   - Kube Prometheus Stack (monitoring)
*   - Metrics Server
*   - Cluster Autoscaler
*
* ## Deployment Instructions:
* 
* ### Prerequisites:
* 1. AWS CLI configured with appropriate credentials
* 2. Terraform >= 1.0 installed
* 3. kubectl installed (for second run)
* 4. Helm installed (for second run)
*
* ### First Run - Cluster Creation:
* 1. Review and update variables in variables.tf if needed (project_name, aws_region, etc.)
* 2. Initialize Terraform:
*    `terraform init`
* 3. Review the execution plan:
*    `terraform plan`
* 4. Apply the configuration to create VPC and EKS cluster:
*    `terraform apply`
* 5. After successful deployment, configure kubectl:
*    `aws eks update-kubeconfig --region <region> --name <cluster-name>`
*    (Use the output value from terraform output configure_kubectl)
*
* ### Second Run - Deploy Addons:
* 1. Uncomment the eks_blueprint.tf file 
* 2. Re-initialize Terraform to download the helm provider:
*    `terraform init`
* 3. Review the execution plan:
*    `terraform plan`
* 4. Apply to deploy EKS Blueprints addons:
*    `terraform apply`
*
* ### Note: The eks_blueprint.tf file is commented out initially because it requires
* the EKS cluster to be created first. The addons depend on the cluster endpoint,
* OIDC provider, and other cluster resources that are created in the first run.
*
* ## Cleanup:
* To destroy all resources:
* `terraform destroy`
*
*/
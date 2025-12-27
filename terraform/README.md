# AIOps-MLOps-Platform

This Terraform configuration deploys a complete MLOps + AIOps platform infrastructure on AWS.
The platform combines:
- MLOps Component: Kubeflow for machine learning model development and deployment
  to predict resource usage (CPU, memory, disk, network)
- AIOps Component: LLM-powered interface for natural language queries and system interaction

## Infrastructure Components:
- VPC: Virtual Private Cloud with public and private subnets across multiple availability zones
- EKS: Amazon Elastic Kubernetes Service cluster for container orchestration
- EKS Blueprints Addons: Essential Kubernetes addons including:
  - AWS Load Balancer Controller
  - Cert Manager
  - Kube Prometheus Stack (monitoring)
  - Metrics Server
  - Cluster Autoscaler

## Deployment Instructions:

### Prerequisites:
1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.0 installed
3. kubectl installed (for second run)
4. Helm installed (for second run)

### First Run - Cluster Creation:
1. Review and update variables in variables.tf if needed (project\_name, aws\_region, etc.)
2. Initialize Terraform:
   `terraform init`
3. Review the execution plan:
   `terraform plan`
4. Apply the configuration to create VPC and EKS cluster:
   `terraform apply`
5. After successful deployment, configure kubectl:
   `aws eks update-kubeconfig --region <region> --name <cluster-name>`
   (Use the output value from terraform output configure\_kubectl)

### Second Run - Deploy Addons:
1. Uncomment the eks\_blueprint.tf file
2. Re-initialize Terraform to download the helm provider:
   `terraform init`
3. Review the execution plan:
   `terraform plan`
4. Apply to deploy EKS Blueprints addons:
   `terraform apply`

### Note: The eks\_blueprint.tf file is commented out initially because it requires
the EKS cluster to be created first. The addons depend on the cluster endpoint,
OIDC provider, and other cluster resources that are created in the first run.

## Cleanup:
To destroy all resources:
`terraform destroy`

## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 5.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 5.100.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_eks"></a> [eks](#module\_eks) | terraform-aws-modules/eks/aws | ~> 20.0 |
| <a name="module_eks_blueprints_addons"></a> [eks\_blueprints\_addons](#module\_eks\_blueprints\_addons) | aws-ia/eks-blueprints-addons/aws | ~> 1.0 |
| <a name="module_vpc"></a> [vpc](#module\_vpc) | terraform-aws-modules/vpc/aws | ~> 5.0 |

## Resources

| Name | Type |
|------|------|
| [aws_iam_role.ebs_csi](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy_attachment.AmazonEBSCSIDriverPolicy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_launch_template.node_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/launch_template) | resource |
| [aws_ami.eks_optimized](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ami) | data source |
| [aws_availability_zones.available](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/availability_zones) | data source |
| [aws_iam_policy_document.ebs_csi_irsa](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_availability_zones"></a> [availability\_zones](#input\_availability\_zones) | List of availability zones | `list(string)` | <pre>[<br/>  "us-east-1a",<br/>  "us-east-1b"<br/>]</pre> | no |
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region for resources | `string` | `"us-east-1"` | no |
| <a name="input_eks_cluster_version"></a> [eks\_cluster\_version](#input\_eks\_cluster\_version) | Kubernetes version for EKS cluster | `string` | `"1.33"` | no |
| <a name="input_eks_node_groups"></a> [eks\_node\_groups](#input\_eks\_node\_groups) | Map of EKS node group configurations | <pre>map(object({<br/>    instance_types = list(string)<br/>    min_size       = number<br/>    max_size       = number<br/>    desired_size   = number<br/>    disk_size      = number<br/>    labels         = optional(map(string), {})<br/>    taints = optional(map(object({<br/>      key    = string<br/>      value  = string<br/>      effect = string<br/>    })), {})<br/>    update_config = optional(object({<br/>      max_unavailable_percentage = optional(number, 50)<br/>    }), {})<br/>    instance_tags = optional(map(string), {})<br/>    volume_tags   = optional(map(string), {})<br/>  }))</pre> | <pre>{<br/>  "main": {<br/>    "desired_size": 2,<br/>    "disk_size": 20,<br/>    "instance_tags": {},<br/>    "instance_types": [<br/>      "t3.medium"<br/>    ],<br/>    "labels": {<br/>      "NodeGroup": "main"<br/>    },<br/>    "max_size": 4,<br/>    "min_size": 1,<br/>    "volume_tags": {}<br/>  },<br/>  "test_managed_np": {<br/>    "desired_size": 1,<br/>    "disk_size": 20,<br/>    "instance_tags": {},<br/>    "instance_types": [<br/>      "t3.small"<br/>    ],<br/>    "labels": {<br/>      "NodeGroup": "test"<br/>    },<br/>    "max_size": 1,<br/>    "min_size": 1,<br/>    "taints": {<br/>      "dedicated": {<br/>        "effect": "NO_SCHEDULE",<br/>        "key": "dedicated",<br/>        "value": "test"<br/>      }<br/>    },<br/>    "volume_tags": {}<br/>  }<br/>}</pre> | no |
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name (dev, staging, prod) | `string` | `"dev"` | no |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | Project name for resource naming | `string` | `"aiops"` | no |
| <a name="input_vpc_cidr"></a> [vpc\_cidr](#input\_vpc\_cidr) | CIDR block for VPC | `string` | `"10.0.0.0/16"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_configure_kubectl"></a> [configure\_kubectl](#output\_configure\_kubectl) | Configure kubectl: make sure you're logged in with the correct AWS profile and run the following command to update your kubeconfig |
| <a name="output_eks_cluster_arn"></a> [eks\_cluster\_arn](#output\_eks\_cluster\_arn) | EKS cluster ARN |
| <a name="output_eks_cluster_endpoint"></a> [eks\_cluster\_endpoint](#output\_eks\_cluster\_endpoint) | Endpoint for EKS control plane |
| <a name="output_eks_cluster_id"></a> [eks\_cluster\_id](#output\_eks\_cluster\_id) | EKS cluster ID |
| <a name="output_eks_cluster_name"></a> [eks\_cluster\_name](#output\_eks\_cluster\_name) | EKS cluster name |
| <a name="output_eks_cluster_security_group_id"></a> [eks\_cluster\_security\_group\_id](#output\_eks\_cluster\_security\_group\_id) | Security group ID attached to the EKS cluster |
| <a name="output_eks_oidc_provider_arn"></a> [eks\_oidc\_provider\_arn](#output\_eks\_oidc\_provider\_arn) | ARN of the OIDC Provider if EKS is enabled |
| <a name="output_private_subnet_ids"></a> [private\_subnet\_ids](#output\_private\_subnet\_ids) | IDs of the private subnets |
| <a name="output_public_subnet_ids"></a> [public\_subnet\_ids](#output\_public\_subnet\_ids) | IDs of the public subnets |
| <a name="output_vpc_cidr_block"></a> [vpc\_cidr\_block](#output\_vpc\_cidr\_block) | CIDR block of the VPC |
| <a name="output_vpc_id"></a> [vpc\_id](#output\_vpc\_id) | ID of the VPC |

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "aiops"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.33"
}


variable "eks_node_groups" {
  description = "Map of EKS node group configurations"
  type = map(object({
    instance_types = list(string)
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
    labels         = optional(map(string), {})
    taints = optional(map(object({
      key    = string
      value  = string
      effect = string
    })), {})
    update_config = optional(object({
      max_unavailable_percentage = optional(number, 50)
    }), {})
    instance_tags = optional(map(string), {})
    volume_tags   = optional(map(string), {})
  }))
  default = {
    main = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 4
      desired_size   = 2
      disk_size      = 20
      labels = {
        NodeGroup = "main"
      }
      instance_tags = {}
      volume_tags   = {}
    }
    test_managed_np = {
      instance_types = ["t3.small"]
      min_size       = 1
      max_size       = 1
      desired_size   = 1
      disk_size      = 20
      labels = {
        NodeGroup = "test"
      }
      taints = {
        dedicated = {
          key    = "dedicated"
          value  = "test"
          effect = "NO_SCHEDULE"
        }
      }
      instance_tags = {}
      volume_tags   = {}
    }
  }
}


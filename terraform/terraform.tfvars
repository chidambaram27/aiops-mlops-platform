aws_region   = "us-east-1"
environment  = "dev"
project_name = "ck-poc"

# VPC Configuration
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]

# EKS Configuration
eks_cluster_version     = "1.33"

eks_node_groups = {
  main = {
    instance_types = ["t3.medium"]
    min_size       = 1
    max_size       = 4
    desired_size   = 2
    disk_size      = 20
    labels = {
      NodeGroup = "main"
    }
  }
  loadtest = {
    instance_types = ["t3.small"]
    min_size = 0
    max_size = 1
    desired_size = 0
    disk_size      = 20
    labels = {
      NodeGroup = "loadtest"
    }
  }
  # vllm = {
  #   instance_types = ["t3.xlarge"]
  #   min_size       = 0
  #   max_size       = 1
  #   desired_size   = 0
  #   disk_size      = 60
  #   labels = {
  #     NodeGroup = "vllm"
  #   }
  #   instance_tags = {
  #     Workload = "vllm"
  #   }
  # }
}
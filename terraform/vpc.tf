# VPC Module - Creates VPC with public and private subnets
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i)]
  public_subnets  = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 10)]

  # Enable NAT Gateway for private subnets
  enable_nat_gateway   = true
  single_nat_gateway   = false # One NAT per AZ for high availability
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags for Kubernetes
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = {
    Name = "${var.project_name}-vpc"
  }
}


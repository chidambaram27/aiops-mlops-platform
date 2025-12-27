provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AIOps"
      Environment = var.environment
      ManagedBy   = "Terraform"
      createdby   = "ck@presidio.com"
      modifiedby  = "ck@presidio.com"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}


provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}


module "eks_blueprints_addons" {
  source  = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.0" #ensure to update this to the latest/desired version

  cluster_name      = module.eks.cluster_name
  cluster_endpoint  = module.eks.cluster_endpoint
  cluster_version   = module.eks.cluster_version
  oidc_provider_arn = module.eks.oidc_provider_arn


  # enable_cluster_proportional_autoscaler = true

  enable_aws_load_balancer_controller = true
  enable_cert_manager                 = true

  enable_kube_prometheus_stack = true
  enable_metrics_server        = true

  enable_cluster_autoscaler = true

  cluster_autoscaler = {
    name          = "cluster-autoscaler"
    chart_version = "9.29.0"
    repository    = "https://kubernetes.github.io/autoscaler"
    namespace     = "kube-system"
    # values      = [templatefile("${path.module}/values.yaml", {})]
  }


  tags = {
    Environment = "dev"
    Name        = "${var.project_name}-eks-cluster"
    createdby   = "ck@presidio.com"
    modifiedby  = "ck@presidio.com"
  }

  depends_on = [module.eks]
}
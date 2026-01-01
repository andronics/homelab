provider "talos" {}

locals {
    controlplane_nodes = {
        "01" = {}
        "02" = {}
    }
    worker_nodes = {
        "01" = {}
        "02" = {}
        "03" = {}
    }
    all_nodes = merge(local.controlplane_nodes, local.worker_nodes)
}

resource "talos_machine_secrets" "machine_secrets" {}

data "talos_machine_configuration" "controlplane" {
    cluster_name = var.talos_cluster_name
    machine_type = "controlplane"
    cluster_endpoint = var.talos_endpoints[0]
    machine_secrets = {
        client_certificate = var.talos_client_configuration.client_certificate
        client_key = var.talos_client_configuration.client_key
        ca_certificate = var.talos_client_configuration.ca_certificate
    }
}

data "talos_client_configuration" "this" {
    cluster_name = var.talos_cluster_name
    client_configuration = talos_mac

}

data "talos_machine_configuration" "worker-01" {

  cluster_name = var.talos_cluster_name
  machine_type = "worker"
  cluster_endpoint = var.talos_endpoints[0]
  machine_secrets = {
    client_certificate = var.talos_client_configuration.client_certificate
    client_key = var.talos_client_configuration.client_key
    ca_certificate = var.talos_client_configuration.ca_certificate
  }
}

data "talos_machine_configuration" "this" {
  cluster_name = var.talos_cluster_name
  client_configuration = var.talos_client_configuration
  cluster_endpoints = var.talos_cluster_endpoints
  nodes = var.talos_nodes
}
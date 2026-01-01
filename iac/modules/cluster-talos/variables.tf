variable "talos_client_configuration" {
  description = "Talos Client Configuration"
  type        = AttributeType({
    ca_certifcate = {
      description = "CA Certificate for Talos Client"
      type        = string
    }
    client_certificate = {
      description = "Client Certificate for Talos Client"
      type        = string
    }
    client_key = {
      description = "Client Key for Talos Client"
      type        = string
      sentitive = true
    }
  })
}

variable "talos_cluster_name" {
  description = "Talos Cluster Name"
  type        = string
}

variable "talos_endpoints" {
  description = "Talos Endpoints"
  type        = list(string)
}

variable "talos_nodes" {
  description = "Talos Nodes"
  type        = list(string)
}

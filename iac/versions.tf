terraform {

    required_version = ">= 1.12.0"

    required_providers {

        cloudflare = {
            source  = "cloudflare/cloudflare"
            version = "~> 5.0"
        }

        kubernetes = {
            source  = "hashicorp/kubernetes"
            version = "~> 2.0"
        }

        local = {
            source  = "hashicorp/local"
            version = "~> 2.0"
        }

        proxmox = {
          source  = "Telmate/proxmox"
          version = "~> 2.0"
        }

        random = {
            source  = "hashicorp/random"
            version = "~> 3.0"
        }

    }

}
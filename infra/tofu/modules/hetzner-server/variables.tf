# infra/tofu/modules/hetzner-server/variables.tf

variable "name" {
  type        = string
  description = "Server hostname. Will also prefix firewall and labels."
}

variable "server_type" {
  type        = string
  description = "Hetnzer Cloud server type. Personal env default: cpx21 (3 vCPU / 4 GB RAM)."
  default     = "cpx21"
}

variable "image" {
  type        = string
  description = "Server image. Default: debian-12 (LTS, minimal). Alternatives: ubuntu-24.04, fedora-40."
  default     = "debian-12"
}

variable "location" {
  type        = string
  description = "Hetzner location. Personal: nbg1 (Nuremberg, EU). Other: fsn1, hel1, ash, hil."
  default     = "nbg1"
}

variable "ssh_keys" {
  type = list(object({
    name       = string
    public_key = string # full PEM: "ssh-ed25519 AAAA... polymath@host"
  }))
  description = "SSH public keys to register with Hetzner and place on server's root."
}

variable "ssh_source_ips" {
  type        = list(string)
  description = "CIDR list allowed to reach SSH. Default = open (0.0.0.0/0). RESTRICT per-env in production."
  default     = ["0.0.0.0/0", "::/0"]
}

variable "labels" {
  type        = map(string)
  description = "Hetzner labels applied to server + firewall."
  default = {
    environment = "personal"
  }
}

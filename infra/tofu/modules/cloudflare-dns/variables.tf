# infra/tofu/modules/cloudflare-dns/variables.tf

variable "domain" {
  type        = string
  description = "Apex domain registered in Cloudflare (e.g. polymath.example.com)."
}

variable "records" {
  type = list(object({
    name     = string           # subdomain or "@" for apex, "*" for wildcard
    type     = string           # A | AAAA | CNAME | MX
    value    = string           # IP / hostname / target
    ttl      = number           # 1 = automatic (proxied), else seconds
    proxied  = bool             # Cloudflare proxy (orange cloud)
    priority = optional(number) # only for MX
  }))
  description = "List of DNS records to create under var.domain. Each must have unique name (used as for_each key)."
  default     = []
}

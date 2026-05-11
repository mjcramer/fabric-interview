# ── Hosted Zone ───────────────────────────────────────────────────────────────
# Creates the Route53 zone for alsotheseer.com.
# After first `terraform apply`, copy the NS records from the output and paste
# them into name.com → Manage DNS → Nameservers for alsotheseer.com.
# DNS propagation takes 5–30 minutes, then ACM validation and all records are
# fully automated from this point on.

resource "aws_route53_zone" "main" {
  name = "alsotheseer.com"
}

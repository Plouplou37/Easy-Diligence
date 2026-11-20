# The Application Load Balancer, the only public entry: it ends HTTPS (with
# the ACM certificate of domain_name) and sends everything to the proxy.
# Without a certificate, HTTP only: for a test, never with real accounts.

locals {
  https = var.certificate_arn != null
  public_url = (
    var.domain_name != null
    ? "${local.https ? "https" : "http"}://${var.domain_name}"
    : "http://${aws_lb.this.dns_name}"
  )
}

resource "aws_security_group" "alb" {
  name        = "${local.prefix}-alb"
  description = "The load balancer: HTTP and HTTPS from anywhere, to the proxy"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  count = local.https ? 1 : 0

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "alb_to_proxy" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.proxy.id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
}

resource "aws_lb" "this" {
  name               = local.prefix
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  # A regeneration, or summaries written on the spot, wait on OpenAI for
  # minutes: the proxy allows 600 s, so does the load balancer.
  idle_timeout               = 600
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "proxy" {
  name                 = "${local.prefix}-proxy"
  port                 = 80
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.this.id
  deregistration_delay = 30

  health_check {
    path                = "/healthz"
    matcher             = "200"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

# HTTP: redirected to HTTPS when there is a certificate, served otherwise.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = local.https ? "redirect" : "forward"
    target_group_arn = local.https ? null : aws_lb_target_group.proxy.arn

    dynamic "redirect" {
      for_each = local.https ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count = local.https ? 1 : 0

  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.proxy.arn
  }
}

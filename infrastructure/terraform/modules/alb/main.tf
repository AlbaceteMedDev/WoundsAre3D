variable "name" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "container_port" {
  type    = number
  default = 8000
}
variable "health_check_path" {
  type    = string
  default = "/healthz"
}
variable "certificate_arn" {
  type        = string
  default     = null
  description = "ACM cert ARN. If null, the listener serves HTTP on 80; otherwise HTTPS on 443 with HTTP->HTTPS redirect."
}
variable "ingress_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "CIDR blocks allowed to reach the ALB. Tighten for non-public services."
}

resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "Public ingress for ${var.name} ALB"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "alb_ingress_http" {
  count             = var.certificate_arn == null ? 1 : 0
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = var.ingress_cidrs
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_ingress_http_redirect" {
  count             = var.certificate_arn == null ? 0 : 1
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = var.ingress_cidrs
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_ingress_https" {
  count             = var.certificate_arn == null ? 0 : 1
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = var.ingress_cidrs
  security_group_id = aws_security_group.alb.id
}

resource "aws_lb" "this" {
  name               = var.name
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  drop_invalid_header_fields = true
  enable_http2               = true
  idle_timeout               = 60

  tags = { Name = var.name }
}

resource "aws_lb_target_group" "this" {
  name        = var.name
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = var.health_check_path
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
    matcher             = "200"
  }

  deregistration_delay = 30
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = var.certificate_arn == null ? [1] : []
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.this.arn
    }
  }

  dynamic "default_action" {
    for_each = var.certificate_arn == null ? [] : [1]
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = var.certificate_arn == null ? 0 : 1
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}

output "dns_name"           { value = aws_lb.this.dns_name }
output "zone_id"            { value = aws_lb.this.zone_id }
output "target_group_arn"   { value = aws_lb_target_group.this.arn }
output "security_group_id"  { value = aws_security_group.alb.id }

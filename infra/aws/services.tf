# The three containers of docker-compose.yml, as ECS services on Fargate, in
# the private subnets:
#
#   Internet ─HTTPS─► load balancer ─► proxy ──/api──► backend ──► RDS
#                                        └──── / ────► frontend
#
# The proxy reaches the two others by their name in the private DNS namespace
# (main.tf), and trusts the X-Forwarded-For of the load balancer, which runs
# in the VPC.

locals {
  namespace = aws_service_discovery_private_dns_namespace.this.name

  logs = {
    for service in ["proxy", "frontend", "backend"] :
    service => {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this.name
        awslogs-region        = var.region
        awslogs-stream-prefix = service
      }
    }
  }
}

# --- Security groups: the load balancer → proxy → frontend and backend ---------------

resource "aws_security_group" "proxy" {
  name        = "${local.prefix}-proxy"
  description = "The proxy: from the load balancer only"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "proxy_from_alb" {
  security_group_id            = aws_security_group.proxy.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
}

resource "aws_security_group" "frontend" {
  name        = "${local.prefix}-frontend"
  description = "The frontend: from the proxy only"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "frontend_from_proxy" {
  security_group_id            = aws_security_group.frontend.id
  referenced_security_group_id = aws_security_group.proxy.id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
}

resource "aws_security_group" "backend" {
  name        = "${local.prefix}-backend"
  description = "The backend: from the proxy only"
  vpc_id      = aws_vpc.this.id
}

resource "aws_vpc_security_group_ingress_rule" "backend_from_proxy" {
  security_group_id            = aws_security_group.backend.id
  referenced_security_group_id = aws_security_group.proxy.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
}

# The containers go out: the images, the secrets, OpenAI, the DNS, and the
# proxy to the two others. Through the NAT gateway for what is outside.
resource "aws_vpc_security_group_egress_rule" "tasks" {
  for_each = {
    proxy    = aws_security_group.proxy.id
    frontend = aws_security_group.frontend.id
    backend  = aws_security_group.backend.id
  }

  security_group_id = each.value
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# --- Service discovery ---------------------------------------------------------------

resource "aws_service_discovery_service" "this" {
  for_each = toset(["frontend", "backend"])

  name = each.key

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.this.id
    routing_policy = "MULTIVALUE"

    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

# --- Backend --------------------------------------------------------------------------
# One task, always on: a run goes on in its process (BackgroundTasks). At a
# deployment, the old task stops before the new one starts: never two runs of
# the migrations, nor two engines, at once. At start, the migrations, then the
# API (backend/Dockerfile).

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.backend.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name         = "backend"
      image        = local.images.backend
      essential    = true
      portMappings = [{ containerPort = 8000, protocol = "tcp" }]
      environment = concat(
        [
          { name = "OPENAI_MODEL", value = var.openai_model },
          # The address put in the password reset e-mails.
          { name = "FRONTEND_URL", value = local.public_url },
        ],
        [for name, value in var.backend_env : { name = name, value = value }],
      )
      secrets = [for name, arn in local.backend_secrets : { name = name, valueFrom = arn }]
      healthCheck = {
        command = [
          "CMD", "python", "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)",
        ]
        interval = 15
        timeout  = 5
        retries  = 3
        # The migrations run before the API answers: room for them.
        startPeriod = 120
      }
      # For ECS Exec (the first administrator, README).
      linuxParameters  = { initProcessEnabled = true }
      logConfiguration = local.logs.backend
    },
  ])
}

resource "aws_ecs_service" "backend" {
  name                               = "backend"
  cluster                            = aws_ecs_cluster.this.id
  task_definition                    = aws_ecs_task_definition.backend.arn
  launch_type                        = "FARGATE"
  desired_count                      = 1
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  enable_execute_command             = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["backend"].arn
  }

  depends_on = [aws_iam_role_policy.execution_secrets]
}

# --- Frontend -------------------------------------------------------------------------

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.prefix}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name         = "frontend"
      image        = local.images.frontend
      essential    = true
      portMappings = [{ containerPort = 80, protocol = "tcp" }]
      healthCheck = {
        command  = ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1/"]
        interval = 15
        timeout  = 5
        retries  = 3
      }
      logConfiguration = local.logs.frontend
    },
  ])
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.frontend.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.frontend.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.this["frontend"].arn
  }
}

# --- Proxy ----------------------------------------------------------------------------

resource "aws_ecs_task_definition" "proxy" {
  family                   = "${local.prefix}-proxy"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name         = "proxy"
      image        = local.images.proxy
      essential    = true
      portMappings = [{ containerPort = 80, protocol = "tcp" }]
      environment = [
        { name = "BACKEND_UPSTREAM", value = "http://backend.${local.namespace}:8000" },
        { name = "FRONTEND_UPSTREAM", value = "http://frontend.${local.namespace}:80" },
        { name = "TRUSTED_PROXIES", value = var.vpc_cidr },
      ]
      healthCheck = {
        command  = ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1/healthz"]
        interval = 15
        timeout  = 5
        retries  = 3
      }
      logConfiguration = local.logs.proxy
    },
  ])
}

resource "aws_ecs_service" "proxy" {
  name                              = "proxy"
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.proxy.arn
  launch_type                       = "FARGATE"
  desired_count                     = 1
  health_check_grace_period_seconds = 30

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.proxy.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.proxy.arn
    container_name   = "proxy"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.http]
}

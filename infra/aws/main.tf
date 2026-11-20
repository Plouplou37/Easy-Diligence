# Easy Diligence on AWS: the shared pieces. The database (database.tf), the
# secrets (secrets.tf), the registry (registry.tf), the load balancer
# (load_balancer.tf) and the services (services.tf) build on them. README.md
# gives the commands, in order.

locals {
  prefix = "${var.name}-${var.environment}"

  tags = merge(
    {
      application = "easy-diligence"
      environment = var.environment
      managed-by  = "terraform"
    },
    var.tags,
  )

  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

data "aws_availability_zones" "available" {
  state = "available"
}

# --- Network ------------------------------------------------------------------------
# Public subnets: the load balancer and the NAT gateway. Private subnets: the
# containers and the database, which nothing outside the VPC reaches. The
# containers go out (OpenAI, the images) through the NAT gateway.

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.prefix}-vpc" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${local.prefix}-igw" }
}

resource "aws_subnet" "public" {
  count = length(local.azs)

  vpc_id            = aws_vpc.this.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)

  tags = { Name = "${local.prefix}-public-${local.azs[count.index]}" }
}

resource "aws_subnet" "private" {
  count = length(local.azs)

  vpc_id            = aws_vpc.this.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 10 + count.index)

  tags = { Name = "${local.prefix}-private-${local.azs[count.index]}" }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = { Name = "${local.prefix}-nat" }
}

# One NAT gateway, in the first zone: enough for this application, and the
# priciest piece of the network (README).
resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = { Name = "${local.prefix}-nat" }

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${local.prefix}-public" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }

  tags = { Name = "${local.prefix}-private" }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# --- Logs and cluster --------------------------------------------------------------

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${local.prefix}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "this" {
  name = local.prefix
}

# --- Service discovery ---------------------------------------------------------------
# The proxy reaches the frontend and the backend by name
# (backend.<namespace>), resolved at every request (proxy/default.conf.template):
# a task replaced by a deployment is reached at its new address at once.

resource "aws_service_discovery_private_dns_namespace" "this" {
  name = "${local.prefix}.internal"
  vpc  = aws_vpc.this.id
}

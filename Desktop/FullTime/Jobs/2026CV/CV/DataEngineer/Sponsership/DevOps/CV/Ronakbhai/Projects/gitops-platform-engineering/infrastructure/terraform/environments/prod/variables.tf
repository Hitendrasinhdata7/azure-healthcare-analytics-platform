variable "vpc_cidr" {
  type = string
}
variable "azs" {
  type = list(string)
}
variable "node_instance_type" {
  type = string
}
variable "min_nodes" {
  type = number
}
variable "max_nodes" {
  type = number
}
variable "desired_nodes" {
  type = number
}

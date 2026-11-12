output "kms_key_arn" {
  value = aws_kms_key.lab.arn
}

output "vpc_id" {
  value = aws_vpc.lab.id
}

output "public_subnet_id" {
  value = aws_subnet.public.id
}

output "private_subnet_id" {
  value = aws_subnet.private.id
}

output "extra_security_group_id" {
  value = aws_security_group.nodes_extra.id
}

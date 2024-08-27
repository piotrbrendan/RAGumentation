output "s3_bucket_name" {
    value = aws_s3_bucket.ragumentation_bucket.bucket
}

output "lambda_functions_arns" {
    value = [module.lambda_doc_parser.lambda_function_arn, module.lambda_chat_handler.lambda_function_arn]
}

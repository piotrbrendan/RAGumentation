resource "aws_s3_bucket" "ragumentation_bucket" {
  bucket_prefix = var.bucket_name_prefix
  force_destroy = true
}

resource "aws_s3_bucket_ownership_controls" "ragumentation_bucket_ownership_controls" {
  bucket = aws_s3_bucket.ragumentation_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# copy data to s3
resource "aws_s3_object" "cp_docs_to_s3" {
  bucket     = aws_s3_bucket.ragumentation_bucket.bucket
  for_each   = fileset("../data", "**/*.zip")
  key        = "${var.raw_docs_prefix}/${each.value}"
  source     = "../data/${each.value}"
  depends_on = [aws_s3_bucket.ragumentation_bucket]
}


data "aws_caller_identity" "current" {}
data "aws_ecr_authorization_token" "token" {}

module "ecr_doc_parser" {
  source                             = "git::https://github.com/terraform-aws-modules/terraform-aws-ecr.git"
  repository_name                    = var.ecr_doc_parser_repository_name
  repository_read_write_access_arns  = [data.aws_caller_identity.current.arn]
  repository_lambda_read_access_arns = [module.lambda_doc_parser.lambda_function_arn]
  create_lifecycle_policy            = false

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
  repository_force_delete = true
}

module "docker_build_from_ecr_doc_parser" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git//modules/docker-build"

  ecr_repo      = module.ecr_doc_parser.repository_name
  use_image_tag = true
  image_tag     = "1.0"
  source_path   = local.doc_parser_source_path
  platform      = "linux/amd64"

}
resource "aws_iam_policy" "aws_ragumentation_lambda_policy" {
  name = "aws_ragumentation_lambda_policy"
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ],
        Resource = [
          "arn:aws:s3:::${aws_s3_bucket.ragumentation_bucket.bucket}",
          "arn:aws:s3:::${aws_s3_bucket.ragumentation_bucket.bucket}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*"
        ]
      }
    ]
    }
  )
}

module "lambda_doc_parser" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git"

  function_name  = "aws-ragumentation-doc-parser"
  create_package = false
  description    = "Lambda function to load the raw documents into the database"
  image_uri      = module.docker_build_from_ecr_doc_parser.image_uri
  timeout        = 900
  memory_size    = 1024
  package_type   = "Image"

  environment_variables = {
    BUCKET_NAME        = aws_s3_bucket.ragumentation_bucket.bucket
    RAW_DOCS_PREFIX    = var.raw_docs_prefix
    VECTOR_DB_PREFIX   = var.vector_db_prefix
    EMBEDDING_MODEL_ID = var.embedding_model_id
  }

  policy_json        = aws_iam_policy.aws_ragumentation_lambda_policy.policy
  attach_policy_json = true
}


module "ecr_chat_handler" {
  source                             = "git::https://github.com/terraform-aws-modules/terraform-aws-ecr.git"
  repository_name                    = var.ecr_chat_handler_repository_name
  repository_read_write_access_arns  = [data.aws_caller_identity.current.arn]
  repository_lambda_read_access_arns = [module.lambda_chat_handler.lambda_function_arn]
  create_lifecycle_policy            = false

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
  repository_force_delete = true
}


module "docker_build_from_ecr_chat_handler" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git//modules/docker-build"

  ecr_repo      = module.ecr_chat_handler.repository_name
  use_image_tag = true # If false, sha of the image will be used TODO: CHECK IF WORKS
  image_tag     = "1.0"

  source_path = local.chat_handler_source_path
  platform    = "linux/amd64"
}

module "lambda_chat_handler" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git"

  function_name  = "aws-ragumentation-chat-handler"
  create_package = false
  description    = "Lambda function to interact with the chatbot and documents base"
  image_uri      = module.docker_build_from_ecr_chat_handler.image_uri
  timeout        = 900
  memory_size    = 1024
  package_type   = "Image"

  environment_variables = {
    BUCKET_NAME        = aws_s3_bucket.ragumentation_bucket.bucket
    VECTOR_DB_PREFIX   = var.vector_db_prefix
    EMBEDDING_MODEL_ID = var.embedding_model_id
    CHAT_MODEL_ID      = var.chat_model_id
  }

  policy_json        = aws_iam_policy.aws_ragumentation_lambda_policy.policy
  attach_policy_json = true
}

# trigger lambda_doc_parser to create the index
resource "aws_lambda_invocation" "invoke_doc_parser" {
  function_name = module.lambda_doc_parser.lambda_function_name
  input         = jsonencode({})
  depends_on    = [module.lambda_doc_parser]
}

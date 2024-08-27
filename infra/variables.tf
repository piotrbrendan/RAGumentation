variable "bucket_name_prefix" {
  type        = string
  description = "The prefix for the bucket to store the documentation"
  default = "aws-ragumentation-project"
}

variable "raw_docs_prefix" {
    type        = string
    description = "The prefix to store the raw documentation (zip files)"
    default = "raw" 
}

variable "vector_db_prefix" {
    type        = string
    description = "The prefix to store the vector database"
    default = "vectordb"
}

variable "embedding_model_id" {
    type        = string
    description = "The id of the AWS Bedrock embedding model"
    default = "cohere.embed-english-v3"
}

variable "chat_model_id" {
    type        = string
    description = "The id of the AWS Bedrock chat model"
    default = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "ecr_doc_parser_repository_name" {
  type        = string
  description = "The name of the ECR repository for the doc parser (i.e. vectordb creation)"
  default = "aws-ragumentation-repository-doc-parser"
}

variable "ecr_chat_handler_repository_name" {
  type        = string
  description = "The name of the ECR repository for the chat handler"
  default = "aws-ragumentation-repository-chat-handler"
}
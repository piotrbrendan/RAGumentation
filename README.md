## AWS Ragumentation
RAG pipeline for AWS documentation exploration.

### 1. How to run
I have used `Makefile` to put together all of the necessary commands. 
The infrastructure is deployed using Terraform. 
For complete solution overview see [Architecture and solution overview](#2-architecture-and-solution-overview)

#### 1.1 Basic setup before first run:

set AWS creds in the `.env` file - this `.env` is used for local Gradio app deployment only
```
# put your environment variables here in a simple format for docker 
# https://docs.docker.com/reference/cli/docker/container/run/#env
MOCK_AWS_CALLS=false
AWS_REGION=us-east-1 # for used 
AWS_ACCESS_KEY_ID=<YOUR_KEY>
AWS_SECRET_ACCESS_KEY=<YOUR KEY>
```

set `region` and `profile` fields `infra/locals.tf` if you want/need to, pls note that it needs to be aligned with `.env` file

```
locals {
  region  = "us-east-1"
  profile = "default"
  doc_parser_source_path = "../lambda/doc_parser"
  chat_handler_source_path = "../lambda/chat_handler"
}
```

#### 1.2. Build infra and deploy AWS based components
`make build_infra` - it will start all the services needed. <br>

#### 1.3 Gradio app local deployment:
Configure `.env` with AWS creds/region etc. (keep it consistent with `infra/locals.tf`)

`make build_app start_app` <br>
Go to http://localhost:7860/ to see the Gradio interface and interact with the RAG pipeline

#### 1.4 Destroy app and infro
`make destroy_all` - stops Gradio app container, destroys image, removes whole infrastructure.


### 2. Architecture and solution overview
![Arch](docs/architecture.svg)

1. Raw data (zip file) is uploaded from local to S3 bucket (using terraform)
2. AWS Lambda processes docs (splits into segments using `MarkdownHeaderTextSplitter`) and ingest them into FAISS vector db. FAISS db is created and dumped to S3. This Lambda is invoked once during deployment, later it can be invoked manually if new data needs to be ingested.
3. Second AWS Lambda is responsible for main processing logic for RAG querying: it receives the event with question from a user (via Gradio app), loads vector db into memory and does the retrieval with a chosen LLM
   1.  I decided to not host vector db - other viable option would be to use AWS OpenSearch (serverless version)
   2.  AWS Bedrock is used for embeddings generation and chat.
4. Both Lambdas are Docker based (due to numpy dependencies problems with simple code zipping), images are stored in ECR.
5. Gradio app serves as a lightweight interface to interact with RAG system, please find attached dockerized app. You can run it locally to see how the system works. I include local deployment for this app (all the rest is AWS-based).

### 3. Assumptions

For this PoC there is a bunch of necessary assumptions that I am making, see below:

1. I assume Terraform, AWS CLI and Docker are installed.
2. I assume all the necessary accesses to AWS Bedrock and models are granted (same applies to other AWS-based accesses)
3. I have developed straightforward RAG pipeline, focusing mostly on making it working end-to-end and being cloud centric. 
4. Pls note that `poetry` was used only for local experiments (and requirements freezing for local Gradio app), I am leaving it as is only for reference.


### 4. Resources: 

For terraform I have borrowed from this:
- https://github.com/terraform-aws-modules/terraform-aws-lambda/tree/master 

Lots of ideas from Langchain documentation


### 5. Closing remarks

1. I have included documentation zip file in the repo for convenience and reproducibility from scratch.
2. First request to Lambda is slower (cold start), subsequent requests are much faster.
3. For the purpose of PoC I suggest lightweight solution with 2 Lambdas, S3 and AWS Bedrock components. This should be refined depending on how big the final dataset is, how big the traffic is, desired latency.
4. Chat model and embedding models are configurable (AWS Bedrock) and defined in

  `infra/terraform.tfvars`
  ```
  # chat models and embeddings ids from AWS Bedrock
  chat_model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  embedding_model_id = "cohere.embed-english-v3"
  ```
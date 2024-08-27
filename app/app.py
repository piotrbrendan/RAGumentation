"""Simple Gradio interface to query the AWS Documentation"""

import json
import os

import boto3
import gradio as gr

MOCK_AWS_CALLS = os.getenv("MOCK_AWS_CALLS", "false").capitalize() == "True"
print(f"MOCK_AWS_CALLS: {MOCK_AWS_CALLS}")

if MOCK_AWS_CALLS is False:
    boto_session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )
    lambda_client = boto_session.client("lambda")


def query_documentation(question: str) -> str:
    """Query the AWS Ragumentation Chat Handler Lambda function and return the response."""
    message = {"input": question}

    if MOCK_AWS_CALLS is True:
        return (
            "Mocked response, to get real response you need to set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_REGION and set MOCK_AWS_CALLS to false in .env file",
            "### Mocked source",
        )
    
    # simple Lambda invocation to interact with the RAG pipeline
    response = lambda_client.invoke(
        FunctionName="aws-ragumentation-chat-handler", InvocationType="RequestResponse", Payload=json.dumps(message)
    )
    status_code = response["StatusCode"]
    result = json.loads(response["Payload"].read().decode("utf-8"))

    if status_code != 200:
        return f"Error {status_code}: {result['body']}"

    result = json.loads(result["body"])
    return result["answer"], result["sources"]


def main():
    with gr.Blocks() as poc_app:
        gr.Markdown("# AWS Ragumentation")
        question = gr.Textbox(lines=2, label="Question")
        gen_btn = gr.Button("Generate")

        answer = gr.Textbox(label="Answer")
        gr.Markdown("### Sources")
        sources = gr.Markdown(label="Sources")

        gen_btn.click(query_documentation, inputs=[question], outputs=[answer, sources])

    poc_app.launch()


if __name__ == "__main__":
    print("Starting the app...")
    main()

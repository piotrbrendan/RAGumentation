FROM public.ecr.aws/lambda/python:3.10

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

COPY doc_parser.py ${LAMBDA_TASK_ROOT}

CMD ["doc_parser.lambda_handler"]
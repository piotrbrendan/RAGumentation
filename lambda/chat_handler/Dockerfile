FROM public.ecr.aws/lambda/python:3.10

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

COPY chat_handler.py ${LAMBDA_TASK_ROOT}

CMD ["chat_handler.lambda_handler"]
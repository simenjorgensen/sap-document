FROM python:3-alpine

COPY ./service /service

RUN pip install --upgrade pip

COPY ./service/requirements.txt /service/requirements.txt

RUN pip install -r /service/requirements.txt

EXPOSE 5000

CMD ["python3", "-u", "./service/service.py"]
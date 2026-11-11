
FROM apache/airflow:3.1.5

COPY requirements-airflow.txt /tmp/requirements-airflow.txt

RUN pip install --no-cache-dir \
    -r /tmp/requirements-airflow.txt

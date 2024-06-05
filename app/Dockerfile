FROM python:3.10.13

WORKDIR /app

COPY . /app/

RUN pip install -r requirements.txt

CMD ["sh", "-c", "cd db && alembic upgrade head && cd .. && pytest && python -m gunicorn --bind=0.0.0.0:${FLASK_PORT} server:app -w=4"]
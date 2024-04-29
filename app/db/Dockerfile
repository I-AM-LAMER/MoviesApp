FROM python:3.10.13

WORKDIR /db

COPY . /db

RUN  pip install -r requirements.txt

CMD ["alembic", "upgrade", "head"]
"""App server module."""

import logging
import os

from flask import Flask, render_template, request, session
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from db.models import Actor, Movie, MoviesApi

# ------ Setup-------

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s :: %(levelname)s :: %(message)s')


def get_db_url() -> str:
    """_summary_

    Returns:
        str: _description_
    """
    PG_VARS = 'POSTGRES_INNER_HOST', 'POSTGRES_INNER_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'
    credentials = {var: os.environ.get(var) for var in PG_VARS}
    return 'postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_INNER_HOST}:{POSTGRES_INNER_PORT}/{POSTGRES_DB}'.format(**credentials)


engine = create_async_engine(get_db_url())
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False,
)
app = Flask(__name__, static_folder='templates/static')
app.json.ensure_ascii = False
app.secret_key = os.urandom(24)


class ObjectDoesNotExists(Exception):
    """_summary_

    Args:
        Exception (_type_): _description_
    """
    def __init__(self, message, *args):
        self.message = message
        super().__init__(message, *args)

# ------ Helpful functions -------


async def get_movies(session_maker: async_sessionmaker[AsyncSession]) -> list[Movie]:
    """_summary_

    Args:
        session_maker (sessionmaker): _description_

    Returns:
        list[Movie]: _description_
    """
    async with session_maker() as session:
        stmt = select(Movie)
        query = await session.execute(stmt)
        result = query.scalars().all()
        return result


async def get_actors(session_maker: async_sessionmaker[AsyncSession]) -> list[Actor]:
    """_summary_

    Args:
        session_maker (sessionmaker): _description_

    Returns:
        list[Movie]: _description_
    """
    async with session_maker() as session:
        stmt = select(Actor)
        query = await session.execute(stmt)
        result = query.scalars().all()
        return result


async def get_movie(movie_id: str, session_maker: async_sessionmaker[AsyncSession]) -> Movie:
    """_summary_

    Args:
        movie_id (str): _description_
        session_maker (sessionmaker): _description_

    Returns:
        Movie: _description_
    """
    async with session_maker() as session:
        stmt = select(Movie).where(Movie.id == movie_id)
        query = await session.execute(stmt)
        result = query.scalars().first()
        if result is None:
            raise ObjectDoesNotExists(
                f'Movie with id `{movie_id}` does not exists')
        return result


async def get_actor(actor_id: str, session_maker: async_sessionmaker[AsyncSession]) -> Actor:
    """_summary_

    Args:
        actor_id (str): _description_
        session_maker (sessionmaker): _description_

    Returns:
        Movie: _description_
    """
    async with session_maker() as session:
        stmt = select(Actor).where(Actor.id == actor_id)
        query = await session.execute(stmt)
        result = query.scalars().first()
        if result is None:
            raise ObjectDoesNotExists(
                f'Actor with id `{actor_id}` does not exists')
        return result

# ------ Main pages -------


@app.get("/")
async def index():
    movies = await get_movies(async_session_maker)
    return render_template(template_name_or_list="index.html", movies=movies)


@app.get("/actors")
async def actors():
    actors = await get_actors(async_session_maker)
    return render_template(template_name_or_list="actors.html", actors=actors)


@app.get("/detail/<string:movie_id>", endpoint='detail')
async def view_movie(movie_id: str):
    movie = await get_movie(movie_id, async_session_maker)
    return render_template(template_name_or_list="detail.html", movie=movie)


@app.get("/actor/<string:actor_id>", endpoint='actor')
async def view_actor(actor_id: str):
    actor = await get_actor(actor_id, async_session_maker)
    return render_template(template_name_or_list="actor.html", actor=actor)

# ------ REST -------


@app.route("/add_movie_actor", methods=['GET', 'POST'])
async def add_movie_actor():
    if request.method == 'POST':
        api = MoviesApi()
        imdb_id = request.form.get('id')
        if imdb_id == None:
            imdb_id = request.json['id']
        if imdb_id.startswith('tt'):
            url = f'https://www.imdb.com/title/{imdb_id}/'
            await api.add_movie(url)
        if imdb_id.startswith('nm'):
            url = f'https://www.imdb.com/name/{imdb_id}/'
            await api.add_actor(url)
        session['message'] = 'Added successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(template_name_or_list="form.html", method='post', link='add_movie_actor', message='' if message is None else message), 201


@app.route("/delete_movie_actor", methods=['GET', 'POST', 'DELETE'])
async def delete_movie_actor():
    if request.method in ('POST', 'DELETE'):
        imdb_id = request.form.get(
            'id') if request.method == 'POST' else request.json['id']
        async with async_session_maker() as async_session:
            async with async_session.begin():
                if imdb_id.startswith('tt'):
                    instance = await async_session.execute(select(Movie).where(Movie.id == imdb_id))
                if imdb_id.startswith('nm'):
                    instance = await async_session.execute(select(Actor).where(Actor.id == imdb_id))
                instance = instance.scalars().first()
                await async_session.delete(instance)
        session['message'] = 'Deleted successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(template_name_or_list="form.html", method='post', link='delete_movie_actor', message='' if message is None else message)


@app.route("/update_movie", methods=['GET', 'POST', 'PUT'])
async def update_movie():
    inst = inspect(Movie)
    attrs = [c_attr.key for c_attr in inst.mapper.column_attrs]
    if request.method in ('POST', 'PUT'):
        data = {}
        if request.method == 'POST':
            for attr in attrs:
                data[attr] = request.form.get(attr)
        if request.method == 'PUT':
            data = request.get_json()
        async with async_session_maker() as async_session:
            async with async_session.begin():
                movie_query = await async_session.execute(select(Movie).where(Movie.id == data['id']))
                movie = movie_query.scalars().first()
                for key, value in data.items():
                    setattr(movie, key, value if value !=
                            '' else getattr(movie, key))
        session['message'] = 'Modified successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(template_name_or_list="update_form.html", method='post', attrs=attrs, link='update_movie', message='' if message is None else message), 201


@app.route("/update_actor", methods=['GET', 'POST', 'PUT'])
async def update_actor():
    inst = inspect(Actor)
    attrs = [c_attr.key for c_attr in inst.mapper.column_attrs]
    if request.method in ('POST', 'PUT'):
        actor_data = {}
        if request.method == 'POST':
            for attr in attrs:
                actor_data[attr] = request.form.get(attr)
        if request.method == 'PUT':
            actor_data = request.get_json()
        async with async_session_maker() as async_session:
            async with async_session.begin():
                actor_query = await async_session.execute \
                (select(Actor).where(Actor.id == actor_data['id']))
                actor = actor_query.scalars().first()
                for field, new_value in actor_data.items():
                    setattr(actor, field, \
                            getattr(actor, field) if new_value == '' else new_value)
        session['message'] = 'Modified successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(template_name_or_list='update_form.html', method='post', \
                           attrs=attrs, link='update_actor', \
                           message='' if message is None else message), 201

# ------ Handlers -------


@app.errorhandler(ObjectDoesNotExists)
def obj_does_not_exists_error(error):
    """_summary_

    Args:
        error (_type_): _description_

    Returns:
        _type_: _description_
    """
    return render_template('404.html'), 404


@app.errorhandler(404)
def not_found_error(error):
    """_summary_

    Args:
        error (_type_): _description_

    Returns:
        _type_: _description_
    """
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """_summary_

    Args:
        error (_type_): _description_

    Returns:
        _type_: _description_
    """
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(port=os.getenv('FLASK_PORT'))

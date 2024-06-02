import logging
import os

from flask import Flask, render_template, request, session
from sqlalchemy import select
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
        return result


async def get_actor(actor_id: str, session_maker: async_sessionmaker[AsyncSession]) -> Movie:
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
        return result

# ------ Main pages -------


@app.get("/")
async def index():
    movies = await get_movies(async_session_maker)
    return render_template(template_name_or_list="index.html", movies=movies)


@app.get("/detail/<string:movie_id>", endpoint='detail')
async def view_movie(movie_id: str):
    movie = await get_movie(movie_id, async_session_maker)
    return render_template(template_name_or_list="detail.html", movie=movie)


@app.get("/actor/<string:actor_id>", endpoint='actor')
async def view_actor(actor_id: str):
    actor = await get_actor(actor_id, async_session_maker)
    return render_template(template_name_or_list="actor.html", actor=actor)

# ------ REST -------


@app.route("/add_movie", methods=['GET', 'POST'])
async def add_movie():
    if request.method == 'POST':
        api = MoviesApi()
        imdb_id = request.form.get('movie_id')
        if imdb_id == None:
            imdb_id = request.json['movie_id']
        movie = await api.get_movie(imdb_id)
        async with async_session_maker() as async_session:
            await api.fill_tables(async_session, [movie,])
        session['message'] = 'Movie has been added successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(template_name_or_list="form.html", method='post', link='add_movie', message='' if message is None else message)


@app.route("/delete_movie", methods=['GET', 'POST', 'DELETE'])
async def delete_movie():
    if request.method in ('POST', 'DELETE'):
        imdb_id = request.form.get(
            'movie_id') if request.method == 'POST' else request.json['movie_id']
        async with async_session_maker() as async_session:
            async with async_session.begin():
                movie_instance = await async_session.execute(select(Movie).where(Movie.id == imdb_id))
                movie_instance = movie_instance.scalars().first()
                await async_session.delete(movie_instance)
        session['message'] = 'Movie has been deleted successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(template_name_or_list="form.html", method='post', link='delete_movie', message='' if message is None else message)

if __name__ == '__main__':
    app.run(port=os.getenv('FLASK_PORT'))
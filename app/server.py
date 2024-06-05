"""App server module."""

import logging
import os

from db.models import Actor, Movie, MoviesApi
from flask import Flask, render_template, request, session
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

# ------ Setup-------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s :: %(levelname)s :: %(message)s',
)


def get_db_url() -> str:
    """Generate the database URL using environment variables.

    This function constructs the database URL
    using the provided environment variables
    for the PostgreSQL database connection.

    Returns:
        str: The constructed database URL.
    """
    pg_vars = (
        'POSTGRES_INNER_HOST',
        'POSTGRES_INNER_PORT',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_DB',
        )
    credentials = {pr: os.environ.get(pr) for pr in pg_vars}
    return (
        'postgresql+psycopg://' +
        '{POSTGRES_USER}:{POSTGRES_PASSWORD}' +
        '@{POSTGRES_INNER_HOST}:{POSTGRES_INNER_PORT}' +
        '/{POSTGRES_DB}'
    ).format(**credentials)


NOT_FOUND = 404
INTERNAL_ERROR = 500
OK = 200
CREATED = 201

engine = create_async_engine(get_db_url())
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False,
)
app = Flask(__name__, static_folder='templates/static')
app.json.ensure_ascii = False
app.secret_key = os.urandom(24)


class ObjectDoesNotExists(Exception):
    """Custom exception class for object does not exist error.

    This exception is raised when attempting
    to access an object that does not exist in the database.

    Args:
        Exception (_type_): Base exception class.
    """

    def __init__(self, message, *args):
        """_summary_.

        Args:
            message (_type_): _description_
            args (_type_): _description_
        """
        self.message = message
        super().__init__(message, *args)

# ------ Helpful functions -------


async def update(obj_data: dict, some_cls: Movie | Actor) -> None:
    """_summary_.

    Args:
        obj_data (dict): _description_
        some_cls (object): _description_
    """
    async with async_session_maker() as async_session:
        async with async_session.begin():
            query = (
                await async_session.execute(
                    select(some_cls).where(some_cls.id == obj_data['id']),
                    )
                )
            instance = query.scalars().first()
            for field, new_value in obj_data.items():
                setattr(
                    instance,
                    field,
                    getattr(instance, field) if new_value == '' else new_value,
                    )


async def get_movies(
    session_maker: async_sessionmaker[AsyncSession],
        ) -> list[Movie]:
    """Asynchronously fetch all movies from the database.

    This function queries the database asynchronously
    for all records of type Movie and returns them.

    Args:
        session_maker (sessionmaker):
        An asynchronous session maker for interacting with the database.

    Returns:
        list[Movie]: A list of Movie objects fetched from the database.
    """
    async with session_maker() as async_session:
        stmt = select(Movie)
        query = await async_session.execute(stmt)
        return query.scalars().all()


async def get_actors(
    session_maker: async_sessionmaker[AsyncSession],
        ) -> list[Actor]:
    """Asynchronously fetch all actors from the database.

    This function queries the database asynchronously
    for all records of type Actor and returns them.

    Args:
        session_maker (sessionmaker):
        An asynchronous session maker for interacting with the database.

    Returns:
        list[Actor]: A list of Actor objects fetched from the database.
    """
    async with session_maker() as async_session:
        stmt = select(Actor)
        query = await async_session.execute(stmt)
        return query.scalars().all()


async def get_movie(
    movie_id: str,
    session_maker: async_sessionmaker[AsyncSession],
        ) -> Movie:
    """Asynchronously fetch a movie by its ID from the database.

    This function queries the database asynchronously
    for a record of type Movie with the specified ID and returns it.

    Args:
        movie_id (str): The ID of the movie to fetch.
        session_maker (sessionmaker):
        An asynchronous session maker for interacting with the database.

    Raises:
        ObjectDoesNotExists: Object does not exists error

    Returns:
        Movie: The Movie object with the specified ID,
        or raises ObjectDoesNotExists if not found.
    """
    async with session_maker() as async_session:
        stmt = select(Movie).where(Movie.id == movie_id)
        query = await async_session.execute(stmt)
        query_result = query.scalars().first()
        if query_result is None:
            raise ObjectDoesNotExists(
                'Movie with id `{0}` does not exists'.format(movie_id),
                )
        return query_result


async def get_actor(
    actor_id: str,
    session_maker: async_sessionmaker[AsyncSession],
        ) -> Actor:
    """Asynchronously fetch an actor by its ID from the database.

    This function queries the database asynchronously
    for a record of type Actor with the specified ID and returns it.

    Args:
        actor_id (str): The ID of the actor to fetch.
        session_maker (sessionmaker):
        An asynchronous session maker for interacting with the database.

    Raises:
        ObjectDoesNotExists: Object does not exists error

    Returns:
        Actor: The Actor object with the specified ID,
        or raises ObjectDoesNotExists if not found.
    """
    async with session_maker() as async_session:
        stmt = select(Actor).where(Actor.id == actor_id)
        query = await async_session.execute(stmt)
        query_result = query.scalars().first()
        if query_result is None:
            raise ObjectDoesNotExists(
                'Actor with id `{0}` does not exists'.format(actor_id),
                )
        return query_result

# ------ Main pages -------


@app.get('/')
async def index():
    """Render the main page displaying a list of movies.

    This route handler renders the main page of the application,
    listing all available movies.

    Returns:
        TemplateResponse: The rendered template for the main page.
    """
    movies = await get_movies(async_session_maker)
    return render_template(template_name_or_list='index.html', movies=movies)


@app.get('/actors')
async def actors():
    """Render the actors page displaying a list of actors.

    This route handler renders the actors page of the application,
    listing all available actors.

    Returns:
        TemplateResponse: The rendered template for the actors page.
    """
    act_seq = await get_actors(async_session_maker)
    return render_template(template_name_or_list='actors.html', actors=act_seq)


@app.get('/detail/<string:movie_id>', endpoint='detail')
async def view_movie(movie_id: str):
    """Render the detail page for a specific movie.

    This route handler renders the detail page
    for a specific movie identified by its ID.

    Args:
        movie_id (str): The ID of the movie to display.

    Returns:
        TemplateResponse: The rendered template for the movie detail page.
    """
    movie = await get_movie(movie_id, async_session_maker)
    return render_template(template_name_or_list='detail.html', movie=movie)


@app.get('/actor/<string:actor_id>', endpoint='actor')
async def view_actor(actor_id: str):
    """Render the detail page for a specific actor.

    This route handler renders the detail page
    for a specific actor identified by its ID.

    Args:
        actor_id (str): The ID of the actor to display.

    Returns:
        TemplateResponse: The rendered template for the actor detail page.
    """
    actor = await get_actor(actor_id, async_session_maker)
    return render_template(template_name_or_list='actor.html', actor=actor)

# ------ REST -------


@app.route('/add_movie_actor', methods=['GET', 'POST'])
async def add_movie_actor():
    """Handle adding a movie or actor via the REST API.

    This route handler processes both GET and POST requests
    to add a movie or actor based on an IMDb ID.

    Returns:
        Tuple[TemplateResponse, int]:
        The response template and HTTP status code indicating success.
    """
    if request.method == 'POST':
        api = MoviesApi()
        imdb_id = request.form.get('id')
        if imdb_id is None:
            imdb_id = request.json['id']
        if imdb_id.startswith('tt'):
            url = 'https://www.imdb.com/title/{0}/'.format(imdb_id)
            await api.add_movie(url)
        if imdb_id.startswith('nm'):
            url = 'https://www.imdb.com/name/{0}/'.format(imdb_id)
            await api.add_actor(url)
        session['message'] = 'Added successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(
        template_name_or_list='form.html', method='post',
        link='add_movie_actor',
        message='' if message is None else message,
    ), CREATED


@app.route('/delete_movie_actor', methods=['GET', 'POST', 'DELETE'])
async def delete_movie_actor():
    """Handle deleting a movie or actor via the REST API.

    This route handler processes GET, POST, and DELETE requests
    to delete a movie or actor based on an IMDb ID.

    Returns:
        Tuple[TemplateResponse, int]:
        The response template and HTTP status code indicating success.
    """
    if request.method in {'POST', 'DELETE'}:
        if request.method == 'POST':
            imdb_id = request.form.get('id')
        else:
            imdb_id = request.json['id']
        async with async_session_maker() as async_session:
            async with async_session.begin():
                if imdb_id.startswith('tt'):
                    instance = (
                        await async_session.execute(
                            select(Movie).where(Movie.id == imdb_id),
                            )
                        )
                if imdb_id.startswith('nm'):
                    instance = (
                        await async_session.execute(
                            select(Actor).where(Actor.id == imdb_id),
                            )
                        )
                instance = instance.scalars().first()
                await async_session.delete(instance)
        session['message'] = 'Deleted successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(
        template_name_or_list='form.html', method='post',
        link='delete_movie_actor',
        message='' if message is None else message,
    )


@app.route('/update_movie', methods=['GET', 'POST', 'PUT'])
async def update_movie():
    """Update a movie's details via the REST API.

    This route handler processes both GET, POST, and PUT requests
    to update a movie's details based on the provided data.

    Returns:
        tuple: A tuple containing the rendered template
        for the update form and the HTTP status code indicating success.
    """
    inst = inspect(Movie)
    attrs = [c_attr.key for c_attr in inst.mapper.column_attrs]
    if request.method in {'POST', 'PUT'}:
        movie_data = {}
        if request.method == 'POST':
            for attr in attrs:
                movie_data[attr] = request.form.get(attr)
        if request.method == 'PUT':
            movie_data = request.get_json()
            logging.info(movie_data)
        await update(movie_data, Movie)
        session['message'] = 'Modified successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(
        template_name_or_list='update_form.html', method='post',
        attrs=attrs, link='update_movie',
        message='' if message is None else message,
    ), OK


@app.route('/update_actor', methods=['GET', 'POST', 'PUT'])
async def update_actor():
    """Update an actor's details via the REST API.

    This route handler processes both GET, POST,
    and PUT requests to update an actor's details based on the provided data.

    Returns:
        tuple: A tuple containing the rendered template
        for the update form and the HTTP status code indicating success.
    """
    inst = inspect(Actor)
    attrs = [c_attr.key for c_attr in inst.mapper.column_attrs]
    if request.method in {'POST', 'PUT'}:
        actor_data = {}
        if request.method == 'POST':
            for attr in attrs:
                actor_data[attr] = request.form.get(attr)
        if request.method == 'PUT':
            actor_data = request.get_json()
        await update(actor_data, Actor)
        session['message'] = 'Modified successfully!'
    message = session.get('message')
    session.pop('message', None)
    return render_template(
        template_name_or_list='update_form.html', method='post',
        attrs=attrs, link='update_actor',
        message='' if message is None else message,
    ), OK

# ------ Handlers -------


@app.errorhandler(ObjectDoesNotExists)
def obj_does_not_exists_error(error):
    """Error handler for ObjectDoesNotExists exceptions.

    This error handler catches
    ObjectDoesNotExists exceptions and renders a 404 Not Found page.

    Args:
        error (ObjectDoesNotExists): The exception instance.

    Returns:
        Tuple[TemplateResponse, int]:
        The response template and HTTP status code indicating an error.
    """
    return render_template('404.html'), NOT_FOUND


@app.errorhandler(NOT_FOUND)
def not_found_error(error):
    """Error handler for generic 404 Not Found errors.

    This error handler catches generic
    404 Not Found errors and renders a 404 Not Found page.

    Args:
        error (_type_): The exception instance.

    Returns:
        Tuple[TemplateResponse, int]:
        The response template and HTTP status code indicating an error.
    """
    return render_template('404.html'), NOT_FOUND


@app.errorhandler(INTERNAL_ERROR)
def internal_error(error):
    """Error handler for generic 500 Internal Server Error.

    This error handler catches generic
    500 Internal Server Error and renders a 500 Internal Server Error page.

    Args:
        error (_type_): The exception instance.

    Returns:
        Tuple[TemplateResponse, int]:
        The response template and HTTP status code indicating an error.
    """
    return render_template('500.html'), INTERNAL_ERROR


if __name__ == '__main__':
    app.run(port=os.getenv('FLASK_PORT'))

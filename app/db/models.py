"""Models and api module."""
import html as HTML
import json
import logging
import os
import uuid
from datetime import date, datetime

from lxml import html
from requests_html import AsyncHTMLSession
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, MappedColumn,
                            mapped_column, relationship)
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    """Base class for declarative models."""


class CreatedMixin(object):
    """Mixin class to automatically set the creation timestamp."""

    created: Mapped[date] = mapped_column(default=datetime.now, nullable=True)


class MovieActor(Base):
    """Association table between movies and actors."""

    __tablename__ = 'movie_actor'
    movie_id: Mapped[str] = mapped_column(ForeignKey('movie.id'), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('actor.id'), primary_key=True)


class MovieGenre(Base):
    """Association table between movies and genres."""

    __tablename__ = 'movie_genre'
    movie_id: Mapped[str] = mapped_column(ForeignKey('movie.id'), primary_key=True)
    genre_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('genre.id'), primary_key=True)


class Movie(CreatedMixin, Base):
    """Represents a movie entity in the database."""

    __tablename__ = 'movie'

    id: Mapped[str] = mapped_column(primary_key=True)
    movie_name: MappedColumn[str]
    url: MappedColumn[str]
    poster: MappedColumn[str]
    description: MappedColumn[str]
    rating: MappedColumn[float]

    genres: Mapped[list['Genre']] = relationship(
        secondary='movie_genre',
        back_populates='movies',
        lazy='selectin',
        )

    actors: Mapped[list['Actor']] = relationship(
        secondary='movie_actor',
        back_populates='movies',
        lazy='selectin',
        )

    __table_args__ = (
        CheckConstraint('length(description) < 300', 'description_valid_length'),
    )


class Actor(CreatedMixin, Base):
    """Represents an actor entity in the database."""

    __tablename__ = 'actor'

    id: Mapped[str] = mapped_column(primary_key=True)
    actor_name: MappedColumn[str]
    image: MappedColumn[str]
    url: MappedColumn[str]
    description: MappedColumn[str]
    birth_date: MappedColumn[date]

    movies: Mapped[list[Movie]] = relationship(
        secondary='movie_actor',
        back_populates='actors',
        lazy='selectin',
        )

    __table_args__ = (
        CheckConstraint('length(description) < 300', 'description_valid_length'),
    )


class Genre(Base):
    """Represents a genre entity in the database."""

    __tablename__ = 'genre'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    genre_name: MappedColumn[str]
    movies: Mapped[list[Movie]] = relationship(
        secondary='movie_genre',
        back_populates='genres',
        lazy='selectin',
        )

    __table_args__ = (
        CheckConstraint('length(genre_name) < 60', 'genre_valid_length'),
        UniqueConstraint('genre_name', name='genre_name_unique_constraint'),
    )


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s :: %(levelname)s :: %(message)s',
)


class MoviesApi(object):
    """Main API class for handling movie, actor, and genre operations."""

    def __init__(self) -> None:
        """Initialize the MoviesApi instance with database and session setup."""
        self.engine = create_async_engine(self.get_db_url(), poolclass=NullPool)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False,
        )()
        Base.metadata.bind = self.engine
        self.session = AsyncHTMLSession()

    @staticmethod
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

    @staticmethod
    def get_id(url: str):
        """Extract the ID from a given URL.

        Args:
            url (str): The URL from which to extract the ID.

        Returns:
            str: The extracted ID.
        """
        return url.split('/')[-2]

    async def insert_data_movie_genre(self, movie: Movie, genre: Genre, session: AsyncSession):
        """Insert or associates a movie with a genre in the database.

        Args:
            movie (Movie): The movie entity.
            genre (Genre): The genre entity.
            session (AsyncSession): The database session.

        """
        async with session.begin():
            movie_stmt = (
                await session.execute(
                    select(Movie).where(Movie.id == movie.id),
                    )
                )
            genre_stmt = (
                await session.execute(
                    select(Genre).where(Genre.genre_name == genre.genre_name),
                    )
                )
            movie_result = movie_stmt.scalars().first()
            genre_result = genre_stmt.scalars().first()
            if genre_result is not None:
                genre = genre_result
            else:
                session.add(genre)
            if movie_result is not None:
                movie = movie_result
            else:
                session.add(movie)
            movie.genres.append(genre)

    async def insert_data_movie_actor(self, movie: Movie, actor: Actor, session: AsyncSession):
        """Insert or associates a movie with an actor in the database.

        Args:
            movie (Movie): The movie entity.
            actor (Actor): The actor entity.
            session (AsyncSession): The database session.

        """
        async with session.begin():
            movie_stmt = (
                await session.execute(
                    select(Movie).where(Movie.id == movie.id),
                    )
                )
            actor_stmt = (
                await session.execute(
                    select(Actor).where(Actor.id == actor.id),
                    )
                )
            movie_result = movie_stmt.scalars().first()
            actor_result = actor_stmt.scalars().first()
            if actor_result is not None:
                actor = actor_result
            else:
                session.add(actor)
            if movie_result is not None:
                movie = movie_result
            else:
                session.add(movie)
            movie.actors.append(actor)

    async def get_person(self, actor_id: str) -> dict:
        """Fetch and returns person data from IMDb based on the provided actor ID.

        Args:
            actor_id (str): The IMDb ID of the actor.

        Returns:
            dict: A dictionary containing the actor's details.
        """
        url = 'https://www.imdb.com/name/{0}/'.format(actor_id)
        logging.info(url)
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': (
                'Mozilla (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                'Chrome/84.0.4147.105 Safari/537.36'
            ),
            'Referer': 'https://www.imdb.com/',
            }

        response = await self.session.get(url=url, headers=headers)
        res_result = html.fromstring(response.content)
        res_result = res_result.xpath("//script[@type='application/ld+json']")
        return json.loads(res_result[0].text)

    async def get_movie(self, movie_id: str) -> dict:
        """Fetch and returns movie data from IMDb based on the provided movie ID.

        Args:
            movie_id (str): The IMDb ID of the movie.

        Returns:
            dict: A dictionary containing the movie's details.
        """
        url = 'https://www.imdb.com/title/{0}/'.format(movie_id)
        logging.info(url)
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': (
                'Mozilla (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
                'Chrome/84.0.4147.105 Safari/537.36'
            ),
            'Referer': 'https://www.imdb.com/',
            }

        response = await self.session.get(url=url, headers=headers)
        res_result = html.fromstring(response.content)
        res_result = res_result.xpath("//script[@type='application/ld+json']")
        return json.loads(res_result[0].text)

    async def add_movie(self, movie_url: str):
        """Add a new movie to the database based on the provided URL.

        Args:
            movie_url (str): The URL of the movie to add.
        """
        movie_id = self.get_id(movie_url)
        movie = await self.get_movie(movie_id)
        logging.info('Producing movie: {0}'.format(movie_id))
        mv = Movie(
            **{
                'id': movie_id,
                'movie_name': HTML.unescape(movie['name']),
                'url': movie['url'],
                'poster': movie['image'],
                'description':  HTML.unescape(movie['description']),
                'rating': movie['aggregateRating']['ratingValue'],
            })
        for genre in movie['genre']:
            logging.info('Producing genre: {0}'.format(genre))
            gn = Genre(
                **{
                    'genre_name': genre,
                })
            try:
                await self.insert_data_movie_genre(mv, gn, self.async_session)
            except Exception as err:
                logging.exception(err)
        for actor in movie['actor']:
            actor_id = self.get_id(actor['url'])
            logging.info('Producing actor: {0}'.format(actor_id))
            actor_info = await self.get_person(actor_id)
            actor_info = actor_info['mainEntity']
            act = Actor(
                **{
                    'id': actor_id,
                    'actor_name': actor_info['name'],
                    'image': actor_info['image'],
                    'url': actor_info['url'],
                    'description': HTML.unescape(actor_info['description']),
                    'birth_date': datetime.strptime(
                        actor_info['birthDate'],
                        '%Y-%m-%d',
                        ).date(),
                })
            try:
                await self.insert_data_movie_actor(mv, act, self.async_session)
            except Exception as exc:
                logging.exception(exc)

    async def add_actor(self, actor_url: str):
        """Add a new actor to the database based on the provided URL.

        Args:
            actor_url (str): The URL of the actor to add.
        """
        actor_id = self.get_id(actor_url)
        logging.info('Producing actor: {0}'.format(actor_id))
        actor_info = await self.get_person(actor_id)
        actor = Actor(
            **{
                'id': actor_id,
                'actor_name': actor_info['name'],
                'image': actor_info['image'],
                'url': actor_info['url'],
                'description': HTML.unescape(actor_info['description']),
                'birth_date': datetime.strptime(
                    actor_info['birthDate'],
                    '%Y-%m-%d',
                    ).date(),
            })
        with self.async_session.begin():
            try:
                self.async_session.add(actor)
            except Exception as exc:
                logging.exception(exc)

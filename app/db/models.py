from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, MappedColumn
from PyMovieDb import IMDB
from json import loads
from datetime import datetime
from requests_html import AsyncHTMLSession
from lxml import html
import html as HTML
import logging
from sqlalchemy import select
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os
import asyncio
from datetime import date, datetime
import uuid

class Base(DeclarativeBase):
    pass

class CreatedMixin:
    created: Mapped[date] = mapped_column(default=datetime.now, nullable=True)

class MovieActor(Base):
    __tablename__ = 'movie_actor'
    movie_id: Mapped[str] = mapped_column(ForeignKey('movie.id'), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('actor.id'), primary_key=True)

class MovieGenre(Base):
    __tablename__ = 'movie_genre'
    movie_id: Mapped[str] = mapped_column(ForeignKey('movie.id'), primary_key=True)
    genre_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('genre.id'), primary_key=True)

class Movie(CreatedMixin, Base):
    __tablename__ = 'movie'

    id: Mapped[str] = mapped_column(primary_key=True)
    movie_name: MappedColumn[str]
    url: MappedColumn[str]
    poster: MappedColumn[str]
    description: MappedColumn[str]
    rating: MappedColumn[float]

    genres: Mapped[list['Genre']] = relationship(secondary='movie_genre' ,back_populates='movies', lazy='selectin')

    actors: Mapped[list['Actor']] = relationship(secondary='movie_actor', back_populates='movies', lazy='selectin')

    __table_args__ = (
        CheckConstraint('length(description) < 300', 'description_valid_length'),
    )

class Actor(CreatedMixin, Base):
    __tablename__ = 'actor'

    id: Mapped[str] = mapped_column(primary_key=True)
    actor_name: MappedColumn[str]
    image: MappedColumn[str]
    url: MappedColumn[str]
    description: MappedColumn[str]
    birth_date: MappedColumn[date]

    movies: Mapped[list[Movie]] = relationship(secondary='movie_actor', back_populates='actors', lazy='selectin')

    __table_args__ = (
        CheckConstraint('length(description) < 300', 'description_valid_length'),
    )

class Genre(Base):
    __tablename__ = 'genre'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    genre_name: MappedColumn[str]
    movies: Mapped[list[Movie]] = relationship(secondary='movie_genre', back_populates='genres', lazy='selectin')

    __table_args__ = (
        CheckConstraint('length(genre_name) < 60', 'genre_valid_length'),
        UniqueConstraint('genre_name', name='genre_name_unique_constraint')
    )

logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')

class MoviesApi:

    def __init__(self) -> None:
        self.engine = create_async_engine(self.get_db_url(), poolclass=NullPool)
        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False
        )()
        Base.metadata.bind = self.engine
        self.session = AsyncHTMLSession()

    @staticmethod
    def get_db_url() -> str:
        PG_VARS = 'POSTGRES_INNER_HOST', 'POSTGRES_INNER_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'
        credentials = {var: os.environ.get(var) for var in PG_VARS}
        return 'postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_INNER_HOST}:{POSTGRES_INNER_PORT}/{POSTGRES_DB}'.format(**credentials)
    
    @staticmethod
    def get_id(url:str):
        return url.split('/')[-2]

    async def insert_data_movie_genre(self, movie: Movie, genre: Genre, session: AsyncSession):
        async with session.begin():
            movie_stmt = await session.execute(select(Movie).where(Movie.id == movie.id))
            genre_stmt = await session.execute(select(Genre).where(Genre.genre_name == genre.genre_name))
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
            if movie_result is not None and genre_result is not None:
                logging.info('Objects of Movie and Genre are already exist')
            else:
                movie.genres.append(genre)

    async def insert_data_movie_actor(self, movie: Movie, actor: Actor, session: AsyncSession):
        async with session.begin():
            movie_stmt = await session.execute(select(Movie).where(Movie.id == movie.id))
            actor_stmt = await session.execute(select(Actor).where(Actor.id == actor.id))
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
            if movie_result is not None and actor_result is not None:
                logging.info('Objects of Movie and Actor are already exist')
            else:
                movie.actors.append(actor)

    async def get_person(self, actor_id:str) -> dict:
        url = f'https://www.imdb.com/name/{actor_id}/'
        logging.info(url)
        headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
                "Referer": "https://www.imdb.com/"
                }

        response = await self.session.get(url=url, headers=headers)
        result = html.fromstring(response.content)
        result = result.xpath("//script[@type='application/ld+json']")
        return loads(result[0].text)

    async def get_movie(self, movie_id:str) -> dict:
        url = f'https://www.imdb.com/title/{movie_id}/'
        logging.info(url)
        headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
                "Referer": "https://www.imdb.com/"
                }

        response = await self.session.get(url=url, headers=headers)
        result = html.fromstring(response.content)
        result = result.xpath("//script[@type='application/ld+json']")
        return loads(result[0].text)
    
    async def add_movie(self, movie_url:str):
            movie_id = self.get_id(movie_url)
            movie = await self.get_movie(movie_id)
            logging.info(f'Producing movie: {movie_id}')
            try:
                mv = Movie(**{
                        "id": movie_id,
                        "movie_name": HTML.unescape(movie['name']),
                        "url": movie['url'],
                        "poster": movie['image'],
                        "description":  HTML.unescape(movie['description']),
                        "rating": movie['aggregateRating']['ratingValue']
                    })
                for genre in movie['genre']:
                    logging.info(f'Producing genre: {genre}')
                    gn = Genre(**{
                                "genre_name": genre
                            })
                    await self.insert_data_movie_genre(mv, gn, self.async_session)
                for actor in movie['actor']:
                    actor_id = self.get_id(actor['url'])
                    logging.info(f'Producing actor: {actor_id}')
                    actor_info = await self.get_person(actor_id)
                    actor_info = actor_info['mainEntity']
                    act =  Actor(**{
                        "id": actor_id,
                        "actor_name": actor_info['name'],
                        "image": actor_info['image'],
                        "url": actor_info['url'],
                        "description": HTML.unescape(actor_info['description']),
                        "birth_date": datetime.strptime(actor_info['birthDate'], "%Y-%m-%d").date()
                    })
                    await self.insert_data_movie_actor(mv, act, self.async_session)  
            except Exception as e:
                logging.exception(e)

    async def add_actor(self, actor_url:str):
        try:
            actor_id = self.get_id(actor_url)
            logging.info(f'Producing actor: {actor_id}')
            actor_info = await self.get_person(actor_id)
            actor = Actor(**{
                            "id": actor_id,
                            "actor_name": actor_info['name'],
                            "image": actor_info['image'],
                            "url": actor_info['url'],
                            "description": HTML.unescape(actor_info['description']),
                            "birth_date": datetime.strptime(actor_info['birthDate'], "%Y-%m-%d").date()
                        })
            with self.async_session.begin():
                self.async_session.add(actor)
        except Exception as e:
            logging.exception(e)
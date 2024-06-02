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
    genre_id: Mapped[int] = mapped_column(ForeignKey('genre.id'), primary_key=True)

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

    id: Mapped[int] = mapped_column(primary_key=True)
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
        Base.metadata.bind = self.engine
        self.session = AsyncHTMLSession()
        self.imdb = IMDB()
        self.res = loads(self.imdb.popular_tv(genre=None, start_id=1, sort_by="Popularity"))
        self.genres = {'Horror', 'Adventure', 'History', 'Action', 'Comedy', 'Biography', 'Family', 'Crime', 'Thriller', 'Fantasy', 'Sci-Fi', 'Drama', 'Animation', 'Mystery', 'Romance', 'Western'}
        self.top_50_films_ids = []
        for result in self.res['results']:
            self.top_50_films_ids.append(result['id'])

        self.genres_table = []

    @staticmethod
    def get_db_url() -> str:
        PG_VARS = 'POSTGRES_INNER_HOST', 'POSTGRES_INNER_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'
        credentials = {var: os.environ.get(var) for var in PG_VARS}
        return 'postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_INNER_HOST}:{POSTGRES_INNER_PORT}/{POSTGRES_DB}'.format(**credentials)

    async def insert_data_movie_genre(self, movie: Movie, genre:  Genre, session: AsyncSession):
        async with session.begin():
            # Проверяем, существует ли жанр в базе данных
            movie_stmt = select( Movie).where( Movie.id ==  Movie.id)
            genre_stmt = select( Genre).where( Genre.id == genre.id)
            movie_query = await session.execute(movie_stmt)
            genre_query = await session.execute(genre_stmt)
            genre_result = genre_query.scalars().first()
            movie_result = movie_query.scalars().first()
            
            if movie_result is None:
                session.add(movie)

            if genre_result is None:
                # Если жанр не существует, добавляем его в базу данных
                session.add(genre)
                
                # Теперь связываем фильм с только что созданным жанром
                movie.genres.append(genre)
                # genre.movies.append(movie)
            else:
                # Если жанр существует, проверяем, связан ли фильм с этим жанром
                if genre_result not in movie.genres:
                    movie.genres.append(genre_result)
                    # genre_result.movies.append(movie)
        

    async def insert_data_movie_actor(self, movie:  Movie, actor:  Actor, session: AsyncSession):
        async with session.begin():
            # Проверяем, существует ли актер в базе данных
            movie_stmt = select( Movie).where( Movie.id == movie.id)
            actor_stmt = select( Actor).where( Actor.id == actor.id)
            movie_query = await session.execute(movie_stmt)
            actor_query = await session.execute(actor_stmt)
            actor_result = actor_query.scalars().first()
            movie_result = movie_query.scalars().first()

            if movie_result is None:
                session.add(movie)
                
            if actor_result is None:
                # Если актер не существует, добавляем его в базу данных
                session.add(actor)
                # Теперь связываем фильм с только что созданным актером
                movie.actors.append(actor)
                # actor.movies.append(movie)
            else:
                # Если актер существует, проверяем, связан ли фильм с этим актером
                if actor_result not in movie.actors:
                    movie.actors.append(actor_result)
                    # actor_result.movies.append(movie)
        

    @staticmethod
    def get_id(url:str):
        return url.split('/')[-2]
                

    def fill_genres_table(self):
        for id, genre in enumerate(self.genres):
            self.genres_table.append(
                {
                    'id': id,
                    'genre': genre
                }
            )

    async def get_person(self, url:str) -> dict:
        headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
                "Referer": "https://www.imdb.com/"
                }

        response = await self.session.get(url=url, headers=headers)
        result = html.fromstring(response.content)
        result = result.xpath("//script[@type='application/ld+json']")
        return loads(result[0].text)

    async def get_movie(self, movie_id:str):
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

    async def movie_generator(self, movie_id:str = None):
        iterable = self.top_50_films_ids if movie_id is None else (movie_id,)
        for movie_id in iterable:
            movie = await self.get_movie(movie_id)
            yield (movie, movie_id)
    
    async def fill_tables(self, async_session:AsyncSession, new_movie:list[dict] = None):
        self.fill_genres_table()
        movie_id = self.get_id(new_movie[0]['url']) if new_movie is not None else None
        movies = self.movie_generator(movie_id)
        async for movie in movies:
            movie_id = movie[1]
            logging.info(f'Producing movie: {movie_id}')
            try:
                mv =  Movie(**{
                        "id": movie_id,
                        "movie_name": HTML.unescape(movie[0]['name']),
                        "url": movie[0]['url'],
                        "poster": movie[0]['image'],
                        "description":  HTML.unescape(movie[0]['description']),
                        "rating": movie[0]['aggregateRating']['ratingValue']
                    })
                for genre in movie[0]['genre']:
                    logging.info(f'Producing genre: {genre}')
                    for data in self.genres_table:
                        if data['genre'] == genre:
                            gn =  Genre(**{
                                        "id": data['id'],
                                        "genre_name": data['genre']
                                    })
                            await self.insert_data_movie_genre(mv, gn, async_session)
                for actor in movie[0]['actor']:
                    actor_id = self.get_id(actor['url'])
                    actor_info = await self.get_person(actor['url'])
                    actor_info = actor_info['mainEntity']

                    logging.info(f'Producing actor: {actor_id}')
                    act =  Actor(**{
                        "id": actor_id,
                        "actor_name": actor_info['name'],
                        "image": actor_info['image'],
                        "url": actor_info['url'],
                        "description": HTML.unescape(actor_info['description']),
                        "birth_date": datetime.strptime(actor_info['birthDate'], "%Y-%m-%d").date()
                    })
                    await self.insert_data_movie_actor(mv, act, async_session)  
            except Exception as e:
                logging.exception(e)
                continue
            
    async def run(self):
        async_session = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        async with async_session() as session:
            stmt = select( Movie)
            query = await session.execute(stmt)
            await session.commit()
            if query.scalars().first() is None:
                await self.fill_tables(session)
        await self.engine.dispose()

if __name__ == '__main__':

    api = MoviesApi()
    asyncio.get_event_loop().run_until_complete(api.run())
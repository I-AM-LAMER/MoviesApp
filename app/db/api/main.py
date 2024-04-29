from PyMovieDb import IMDB
from json import loads
from datetime import datetime
from requests_html import AsyncHTMLSession
from lxml import html
import html as HTML
from typing import Any
import logging
import dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.main import Base, Movie, Genre, Actor
import os


logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')

class MoviesApi:

    def __init__(self) -> None:
        self.engine = create_async_engine(self.get_db_url())
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
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
        dotenv.load_dotenv()
        PG_VARS = 'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'
        credentials = {var: os.environ.get(var) for var in PG_VARS}
        return 'postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'.format(**credentials)

    async def insert_data(self, *args):
        async with self.async_session() as session:
            async with session.begin():
                session.add_all(*args)

    @staticmethod
    def get_id(actor_url:str):
        return actor_url.split('/')[-2]
                

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
        headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
                "Referer": "https://www.imdb.com/"
                }

        response = await self.session.get(url=url, headers=headers)
        result = html.fromstring(response.content)
        result = result.xpath("//script[@type='application/ld+json']")
        return loads(result[0].text)

    async def movie_generator(self):
        for movie_id in self.top_50_films_ids:
            movie = await self.get_movie(movie_id)
            yield (movie, movie_id)
    
    async def fill_tables(self):
        movies = self.movie_generator()
        async for movie in movies:
            movie_id = movie[1]
            logging.info(f'Producing movie: {movie_id}')
            try:
                mv = Movie(**{
                        'id': movie_id,
                        'movie_name': movie[0]['name'],
                        'url': movie[0]['url'],
                        'poster': movie[0]['image'],
                        'description': movie[0]['description'],
                        'rating': movie[0]['aggregateRating']['ratingValue']
                    })
                for genre in movie[0]['genre']:
                    for data in self.genres_table:
                        if data['genre'] == genre:
                            genre_stmt = select(Genre).where(Genre.id == data['id'])
                            genre_query = await self.session.scalars(genre_stmt).one_or_none()
                            if genre_query is None:
                                gn = Genre(**{
                                        'id': data['id'],
                                        'genre_name': data['genre']
                                    })
                                mv.genres.append(gn)
                                gn.movies.append(mv)
                                await self.insert_data(gn)
                            else:
                                mv.genres.append(genre_query)
                                genre_query.movies.append(mv)
                for actor in movie[0]['actor']:
                    actor_id = self.get_id(actor['url'])
                    actor_info = await self.get_person(actor['url'])
                    actor_info = actor_info['mainEntity']

                    logging.info(f'Producing actor: {actor_id}')
                    act_stmt = select(Actor).where(Actor.id == actor_id)
                    act_query = await self.session.scalar(act_stmt).one_or_none()
                    if act_query is None:
                        act = Actor(**{
                            'id': actor_id,
                            'actor_name': actor_info['name'],
                            'image': actor_info['image'],
                            'url': actor_info['url'],
                            'description': HTML.unescape(actor_info['description']),
                            'birth_date': datetime.strptime(actor_info['birthDate'], "%Y-%m-%d").date()
                        })
                        act.movies.append(mv)
                        mv.actors.append(act)
                        await self.insert_data(act)
                    else:
                        act_query.movies.append(mv)
                        mv.actors.append(act_query)

                await self.insert_data(mv)
                await self.session.commit()       
            except Exception as e:
                logging.info(e)
                continue
            
    def run(self):
        self.fill_genres_table()
        self.session.run(self.fill_tables)

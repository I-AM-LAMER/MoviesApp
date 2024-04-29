from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, MappedColumn

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

    genres: Mapped[list['Genre']] = relationship(secondary=MovieGenre ,back_populates='movies')

    actors: Mapped[list['Actor']] = relationship(secondary=MovieActor, back_populates='movies')

    __table_args__ = (
        CheckConstraint('length(description) < 50', 'description_valid_length'),
    )

class Actor(CreatedMixin, Base):
    __tablename__ = 'actor'

    id: Mapped[str] = mapped_column(primary_key=True)
    actor_name: MappedColumn[str]
    image: MappedColumn[str]
    url: MappedColumn[str]
    description: MappedColumn[str]
    birth_date: MappedColumn[date]

    movies: Mapped[list[Movie]] = relationship(secondary=MovieActor, back_populates='actors')

    __table_args__ = (
        CheckConstraint('length(description) < 100', 'description_valid_length'),
    )

class Genre(Base):
    __tablename__ = 'genre'

    id: Mapped[int] = mapped_column(primary_key=True)
    genre_name: MappedColumn[str]
    movies: Mapped[list[Movie]] = relationship(secondary=MovieGenre, back_populates='genres')

    __table_args__ = (
        CheckConstraint('length(genre_name) < 30', 'genre_valid_length'),
        UniqueConstraint('genre_name', name='genre_name_unique_constraint')
    )
 


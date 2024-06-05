import pytest
from server import app 
import asyncio


@pytest.mark.asyncio
async def test_add_movie_actor():
    def sync_test():
        with app.test_client() as test_client:
            response = test_client.post('/add_movie_actor', json={'id': 'tt1853728'})
            assert response.status_code == 201  # Assuming successful operation returns 201 OK
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


@pytest.mark.asyncio
async def test_update_movie():
    def sync_test():
        with app.test_client() as test_client:
            response = test_client.put('/update_movie', json={'id': 'tt1853728', 'movie_name': 'New Title'})
            assert response.status_code == 200  # Assuming successful operation returns 201 OK
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)

@pytest.mark.asyncio
async def test_update_actor():
    def sync_test():
        with app.test_client() as test_client:
            response = test_client.put('/update_actor', json={'id': 'nm0004937', 'actor_name': 'New Title'})
            assert response.status_code == 200  # Assuming successful operation returns 201 OK
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)

@pytest.mark.asyncio
async def test_delete_movie_actor():
    def sync_test():
        with app.test_client() as test_client:
            response = test_client.delete('/delete_movie_actor', json={'id': 'tt1853728'})
            assert response.status_code == 200  # Assuming successful operation returns 201 OK
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)
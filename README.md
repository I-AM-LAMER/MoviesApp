# Launch Instructions:

### 1. Clone a project.
`git clone https://github.com/I-AM-LAMER/MoviesApp`

### 2. Create an .env file.

```
POSTGRES_HOST=<change_me>
POSTGRES_INNER_HOST=postgres
POSTGRES_PORT=<change_me>
POSTGRES_INNER_PORT=5432
POSTGRES_USER=<change_me>
POSTGRES_PASSWORD=<change_me>
POSTGRES_DB=<change_me>
FLASK_PORT=<change_me>
DEBUG_MODE=true | false
```
### 3. Launch a project.

Launch for the first time: `docker compose up --build`
In subsequent times: `docker compose up`
Stop the work: `docker compose stop`
Reset all project settings: `docker compose down`

### 6. Go to the website.
http://0.0.0.0:FLASK_PORT
# survey

# survey Web Interview System

## Description

This is the Web Interview System (WIS) component of Auth.

## Dependencies

The project is packaged with [Poetry](https://python-poetry.org/), so the Python part is covered by that.

Then, install [PostgreSQL](https://www.postgresql.org/download/) to run the database.

## Run

### Run locally

First of all, create an `.env` file at the project's root directory, containing the following environment variables:

```properties

# Database
LEADER_DB_HOST=<database host>
LEADER_DB_PORT=<database port>
LEADER_DB_NAME=<database name>
LEADER_DB_USER=<database user>
LEADER_DB_PASS=<database password>
LEADER_DB_USER_TEST=<test database user>
LEADER_DB_ENGINE_OPTIONS=<SQLAlchemy's engine options, in JSON. defaults to '{"future": true, "pool_pre_ping": true}'>

```

Then, install the project's dependencies:

```shell
poetry install
```

Then, run the following command to start the backend.

> ☝ To initialize the database with tables and data, see [Initialization](#initialization)


```shell
uvicorn app.main:app --reload --port 8000
```

Backend will be accessible @ [http://localhost:8000](http://localhost:8000).

If you wish to make the backend available to the whole network, add `--host 0.0.0.0` to the above command.

If you want to see the OpenAPI docs for the backend make sure you have set the `SHOW_API_DOCS=True`, either in the `.env`
file or directly exporting it in your terminal `export SHOW_API_DOCS=True`. You will then be able to access it
on [http://localhost:8000/docs](http://localhost:8000/docs).

## Project structure

Under `app` folder we have the core code for the application. Then this is split into multiple folders, the most important are:

- `db` is where the database connection is set, redis is connected and under the `models.py` we can find the database models.


- `rotues` is where we define almost every route (with a few exceptions, some routes are defined in that `main.py`

- `schemas` is the folder where the DTOs (Data Transfer Objects) are defined, for both send and request

Under `cli` we have some console scripts that help do different operations on the app like managing the database and others.

Then under `tests`, the tests for the app are defined.

## CLI scripts

As mentioned in the previous section, we have the `cli` folder when we have console utilities (scripts). In order to run them, make sure you are at the root of the project and run `python -m clie.<cli_file_name>`, where `<cli_file_name>` is the file name of the script you want to run.


## Database Management

### Initialization

To perform the initialization you need to have installed [PostgreSQL](https://www.postgresql.org/download/) on your machine.

Since we are using a script to generate the table structure based on the JSON schema, we are using the generated SQL script (named the dump) to create tables and import data (actual rows in the table) that we can work with.

The import scripts can be found on the following drive: https://drive.google.com/drive/u/1/folders/1WDKHifG4GhUU-p4C80AzMVy5xVUNcBUt

The latest dump is the one that has the last modified date as most recent based on the current date.

Once you download the dump, you just need to copy it in some folder and open a terminal on the folder, then run: `psql db < [path_to_db_dump]`.

### Management via CLI

An alternative way of initializing the database is via CLI. Use the commands sequence below to initialize the database
schema and optionally fill the table with sample data for testing purposes. From the project's root directory:

```shell
    $ poetry shell
    > python -m cli.manage_db drop-all
    > python -m cli.manage_db create-all
    > python -m cli.manage_db create-user testadmin testpass --superuser
```



## Running unit tests

Unit tests run on a test database based on [SQLite](https://www.sqlite.org/download.html). The test database is created into the `tmp` subdirectory of the
project's root, so this directory must be present for the unit tests to work properly.
From the project's root directory:

```shell
    $ mkdir tmp
    $ poetry shell
    > pytest
```

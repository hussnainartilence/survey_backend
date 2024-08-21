""" CLI commands for building forms """

import json

import typer

from app.db.database import DBManager

from app.migration_tools import FormMigrationDataBuilder


# create CLI app
app = typer.Typer()


# ASYNC FUNCTIONS


async def async_create(path: str) -> None:
    """
    Asynchronous function to create forms.
    """
    # load form specification
    with open(path, encoding="utf-8") as f_spec:
        j_spec = json.load(f_spec)

    db_manager = DBManager()
    async with db_manager.get_session() as session:
        # validates and builds the schema
        form_spec = CreateForm(**j_spec)
        # builds the form
        builder = FormBuilder()
        await builder.build(spec=form_spec, session=session)



if __name__ == "__main__":
    # start CLI App
    app()

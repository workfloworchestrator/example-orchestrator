# Copyright 2019-2023 SURF.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from contextlib import closing
from pathlib import Path
from typing import cast

import orchestrator
import pytest
from alembic import command
from alembic.config import Config
from fastapi import Depends
from nwastdlib.debugging import start_debugger
from oauth2_lib.settings import oauth2lib_settings
from orchestrator import OrchestratorCore, app_settings
from orchestrator.db import db
from orchestrator.db.database import (
    ENGINE_ARGUMENTS,
    SESSION_ARGUMENTS,
    BaseModel,
    Database,
    SearchQuery,
)
from pytest_postgresql import factories
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import scoped_session, sessionmaker

from tests.unit_tests.factories.node import make_node_subscription

# Start a local postgresql instance
# This might be handy for CICD pipeline configs that don't allow you to drop the DB
test_db = factories.postgresql_proc(dbname="test_db", port=None)


def run_migrations(db_uri: str) -> None:
    """Configure the alembic context and run the migrations.

    Each test will start with a clean database. This a heavy operation but ensures that our database is clean and
    tests run within their own context.

    Args:
        db_uri: The database uri configuration to run the migration on.

    Returns:
    ---
        None

    """
    path = Path(__file__).resolve().parent
    os.environ["DATABASE_URI"] = db_uri
    app_settings.DATABASE_URI = db_uri  # type: ignore
    alembic_cfg = Config(file_=path / "../../alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_uri)

    version_locations = alembic_cfg.get_main_option("version_locations")
    alembic_cfg.set_main_option(
        "version_locations", f"{version_locations} {os.path.dirname(orchestrator.__file__)}/migrations/versions/schema"
    )

    command.upgrade(alembic_cfg, "heads")


@pytest.fixture(scope="session")
def db_uri(worker_id, test_db):
    """Ensure each pytest thread has its database.

    When running tests with the -j option make sure each test worker is isolated within its own database.

    Args:
        worker_id: the worker id
        test_db: test database fixture

    Returns:
    ---
        Database uri to be used in the test thread

    """
    database_uri = f"postgresql://{test_db.user}:{test_db.password}@{test_db.host}:{test_db.port}/{test_db.dbname}"
    if worker_id == "master":
        # pytest is being run without any workers
        return database_uri
    url = make_url(database_uri)
    url = url.set(database=f"{url.database}-{worker_id}")
    return url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def database(db_uri):
    """Create database and run migrations and cleanup afterward.

    Args:
        db_uri: fixture for providing the application context and an initialized database.
    """
    db.update(Database(db_uri))
    url = make_url(db_uri)
    db_to_create = url.database
    url = url.set(database="postgres")

    engine = create_engine(url)
    with closing(engine.connect()) as conn:
        conn.execute(text("COMMIT;"))
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_to_create}";'))
        conn.execute(text("COMMIT;"))
        conn.execute(text(f'CREATE DATABASE "{db_to_create}";'))

    run_migrations(db_uri)
    db.wrapped_database.engine = create_engine(db_uri, **ENGINE_ARGUMENTS)

    try:
        yield
    finally:
        db.wrapped_database.engine.dispose()
        with closing(engine.connect()) as conn:
            conn.execute(text("COMMIT;"))
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_to_create}";'))


@pytest.fixture(autouse=True)
def db_session(database):
    """Ensure tests are run in a transaction with automatic rollback.

    This implementation creates a connection and transaction before yielding to the test function. Any transactions
    started and committed from within the test will be tied to this outer transaction. From the test function's
    perspective it looks like everything will indeed be committed; allowing for queries on the database to be
    performed to see if functions under test have persisted their changes to the database correctly. However once
    the test function returns this fixture will clean everything up by rolling back the outer transaction; leaving the
    database in a known state (=empty with the exception of what migrations have added as the initial state).

    Args:
        database: fixture for providing an initialized database.

    """
    with closing(db.wrapped_database.engine.connect()) as test_connection:
        db.wrapped_database.session_factory = sessionmaker(**SESSION_ARGUMENTS, bind=test_connection)
        db.wrapped_database.scoped_session = scoped_session(
            db.wrapped_database.session_factory, db.wrapped_database._scopefunc
        )
        BaseModel.set_query(cast(SearchQuery, db.wrapped_database.scoped_session.query_property()))

        trans = test_connection.begin()
        try:
            yield
        finally:
            trans.rollback()


@pytest.fixture(scope="session", autouse=True)
def fastapi_app(database, db_uri):
    start_debugger()
    # Todo: implement a proper app factory, for now mimic the app in main.py
    app_settings.DATABASE_URI = db_uri
    # Todo: do we want redis in the pipeline? (speed up tests)
    # app_settings.CACHE_DOMAIN_MODELS = True
    oauth2lib_settings.OAUTH2_ACTIVE = False
    app = OrchestratorCore(base_settings=app_settings)
    import products  # noqa: F401  Side-effects
    import workflows  # noqa: F401  Side-effects

    app.register_graphql()
    app.router.routes = [
        route for route in app.router.routes if not route.__dict__["path"] == "/api/translations/{language}"
    ]
    app.include_router(api_router, prefix="/api", dependencies=[Depends(security.authenticate)])

    register_forms()
    return app


@pytest.fixture()
def node_subscription():
    return make_node_subscription()


# @pytest.fixture()
# def port_subscription():
#     return make_port_subscription()

# @pytest.fixture()
# def core_link_subscription():
#     return make_core_link_subscription()

# @pytest.fixture()
# def l2vpn_subscription():
#     return make_l2vpn_subscription()

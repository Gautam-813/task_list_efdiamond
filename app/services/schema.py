from sqlalchemy import inspect, text


def ensure_sqlite_schema(engine) -> None:
    if not engine.url.drivername.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    with engine.begin() as connection:
        if "assigned_remarks" not in task_columns:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN assigned_remarks TEXT DEFAULT ''")
            )

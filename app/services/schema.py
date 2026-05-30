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
        if "priority" not in task_columns:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'")
            )

    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "task_activity_logs" not in table_names:
            connection.execute(
                text(
                    """CREATE TABLE task_activity_logs (
                        id INTEGER NOT NULL PRIMARY KEY,
                        task_id INTEGER NOT NULL REFERENCES tasks(id),
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        action VARCHAR(255) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )"""
                )
            )
            connection.execute(text("CREATE INDEX ix_task_activity_logs_id ON task_activity_logs(id)"))
            connection.execute(text("CREATE INDEX ix_task_activity_logs_task_id ON task_activity_logs(task_id)"))

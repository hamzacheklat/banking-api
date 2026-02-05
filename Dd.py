

    engine = DatabasesConfig().get_db_engine()

    try:
        with engine.begin() as conn:  # auto commit / rollback
            conn.execute(sql, sql_row)
        return sql_row, ""
    except Exception as e:
        return sql_row, str(e)

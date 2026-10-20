from sqlalchemy import inspect, Table, Column, MetaData, text
from sqlalchemy.dialects.postgresql import (
    VARCHAR,
    TEXT,
    INTEGER,
    BIGINT,
    SMALLINT,
    NUMERIC,
    DOUBLE_PRECISION,
    DATE,
    TIME,
    TIMESTAMP,
)
from config.connection import fb_engine, pg_engine


def map_firebird_to_postgres_type(fb_type):
    """Maps Firebird SQL types to optimized PostgreSQL types."""
    type_name = str(fb_type).upper()

    if "VARCHAR" in type_name:
        length = getattr(fb_type, "length", None)
        return VARCHAR(length) if length else TEXT
    elif "CHAR" in type_name:
        length = getattr(fb_type, "length", None)
        return VARCHAR(length)
    elif "TEXT" in type_name or "BLOB" in type_name:
        return TEXT
    elif "BIGINT" in type_name:
        return BIGINT
    elif "INTEGER" in type_name:
        return INTEGER
    elif "SMALLINT" in type_name:
        return SMALLINT
    elif "NUMERIC" in type_name or "DECIMAL" in type_name:
        precision = getattr(fb_type, "precision", None)
        scale = getattr(fb_type, "scale", None)
        return NUMERIC(precision, scale)
    elif "FLOAT" in type_name or "DOUBLE" in type_name:
        return DOUBLE_PRECISION
    elif "TIMESTAMP" in type_name:
        return TIMESTAMP
    elif "DATE" in type_name:
        return DATE
    elif "TIME" in type_name:
        return TIME
    else:
        return TEXT


def deploy_warehouse_schemas(
    table_list, schema_name="bronze", if_exists_behavior="skip"
):
    """
    Loops through Firebird tables, reads types and primary keys,
    and provisions matching structures safely inside a specific PostgreSQL schema.
    """
    # 💥 Ensure the schema namespace exists in PostgreSQL first
    with pg_engine.begin() as pg_conn:
        pg_conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))
        print(f"📁 Ensured PostgreSQL schema namespace '{schema_name}' exists.")

    fb_inspector = inspect(fb_engine)
    pg_inspector = inspect(pg_engine)
    pg_metadata = MetaData()

    print(
        f"🚀 Starting Warehouse Schema Initialization for {len(table_list)} tables in schema '{schema_name}'..."
    )
    print(f"🔒 Production Rule Set: If table exists -> {if_exists_behavior.upper()}\n")

    successful_mappings = 0

    for source_table in table_list:
        source_table_clean = source_table.strip().upper()
        target_table_name = (
            source_table_clean.lower()
        )  # No prefix, clean table name (e.g., att_reg)

        # Check if table already exists in the designated PostgreSQL schema
        table_exists = pg_inspector.has_table(target_table_name, schema=schema_name)

        if table_exists:
            if if_exists_behavior == "skip":
                print(
                    f"ℹ️ [SKIP] Table '{schema_name}.{target_table_name}' already exists in PostgreSQL. Skipping."
                )
                continue
            elif if_exists_behavior == "drop":
                print(
                    f"🔥 [DROP] Table '{schema_name}.{target_table_name}' already exists. Dropping for recreation."
                )
                temp_meta = MetaData()
                Table(target_table_name, temp_meta, schema=schema_name)
                temp_meta.drop_all(pg_engine)

        print(
            f"📦 [MAPPING] Fetching layout and PKs from Firebird: {source_table_clean} ➔ {schema_name}.{target_table_name}"
        )

        # 1. Fetch column and primary key details from Firebird
        try:
            columns = fb_inspector.get_columns(source_table_clean)
            pk_constraint = fb_inspector.get_pk_constraint(source_table_clean)
            pk_cols = (
                pk_constraint.get("constrained_columns", []) if pk_constraint else []
            )

            if not columns:
                print(
                    f"⚠️ Warning: Firebird table '{source_table_clean}' is empty/invalid. Skipping.\n"
                )
                continue
        except Exception as e:
            print(f"❌ Failed to read Firebird table '{source_table_clean}': {e}\n")
            continue

        # 2. Re-map columns explicitly and attach Primary Keys
        pg_columns = []
        for col in columns:
            col_original_name = col["name"]
            col_name_lower = col_original_name.lower()
            fb_type = col["type"]
            pg_type = map_firebird_to_postgres_type(fb_type)
            is_nullable = col.get("nullable", True)

            # Identify if this column is part of the primary key constraint
            is_pk = col_original_name in pk_cols
            if is_pk:
                print(f"   🔑 Identified Primary Key Column: {col_original_name}")

            pg_columns.append(
                Column(col_name_lower, pg_type, primary_key=is_pk, nullable=is_nullable)
            )

        # Append data lineage ingestion tracker column
        pg_columns.append(Column("dw_ingested_at", TIMESTAMP, nullable=False))

        # 3. Queue up blueprint for execution bound to the schema target namespace
        Table(target_table_name, pg_metadata, schema=schema_name, *pg_columns)
        successful_mappings += 1

    # 4. Deploy schema blueprints to the target warehouse
    if successful_mappings > 0:
        print(
            f"\n🏗️ Deploying {successful_mappings} new table configurations with PKs to PostgreSQL schema '{schema_name}'..."
        )
        try:
            pg_metadata.create_all(pg_engine)
            print(f"✅ Database warehouse bronze schema tables deployed successfully!")
        except Exception as e:
            print(f"❌ Structural deployment crashed: {e}")
    else:
        print("\n🏁 Finished execution. Zero structural updates required.")


if __name__ == "__main__":
    PRODUCTION_TABLES = [
        "ATT_REG",
        "ATT_TYP",
        "EMP_EMP",
        "WGR_AFD",
        "ITA_ETY",
        "ITA_GRD",
        "ITA_NAT",
        "ITA_CON",
        "ITA_SLT",
        "ITA_POS",
        "WGR_BRA",
        "ITA_RLG",
    ]

    # Run the builder script mapping directly into 'bronze' schema with clean names
    deploy_warehouse_schemas(
        table_list=PRODUCTION_TABLES, schema_name="bronze", if_exists_behavior="skip"
    )

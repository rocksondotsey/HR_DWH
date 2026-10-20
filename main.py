
import sys
from datetime import datetime
from config.connection import fb_engine, pg_engine, test_connection
from pipelines.generate_all_schemas import deploy_warehouse_schemas
from pipelines.load_bronze_tables import load_all_bronze_data


def run_master_pipeline():
    print("=" * 70)
    print(f"🚀 INITIALIZING HR DATA WAREHOUSE EXTRACTION PIPELINE")
    print("=" * 70)

    # Phase 1: Health Check
    fb_ok = test_connection(fb_engine, "Source System (Firebird CRM)")
    pg_ok = test_connection(pg_engine, "Target Warehouse (PostgreSQL)")
    if not (fb_ok and pg_ok):
        sys.exit(1)

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

    # Target configuration
    TARGET_SCHEMA = "bronze"

    # Phase 2: Schema Processing
    print(
        f"\n🏗️ PHASE 2: Reconciling Target Schema Layouts inside '{TARGET_SCHEMA}'..."
    )
    deploy_warehouse_schemas(
        table_list=PRODUCTION_TABLES,
        schema_name=TARGET_SCHEMA,
        if_exists_behavior="skip",  # Change to "drop" if resetting structures completely
    )

    # Phase 3: Data Load Processing
    print(f"\n📥 PHASE 3: Streaming Records to '{TARGET_SCHEMA}' Layer...")
    load_all_bronze_data(
        table_list=PRODUCTION_TABLES, schema_name=TARGET_SCHEMA, chunk_size=5000
    )


if __name__ == "__main__":
    start_time = datetime.now()
    run_master_pipeline()
    print(f"\n🏁 MASTER PIPELINE COMPLETE. Duration: {datetime.now() - start_time}")

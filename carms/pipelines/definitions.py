from dagster import Definitions, define_asset_job, load_asset_checks_from_modules, load_assets_from_modules

from carms.core.database import init_db
from carms.pipelines import checks as asset_checks
from carms.pipelines.bronze import assets as bronze_assets
from carms.pipelines.gold import assets as gold_assets
from carms.pipelines.silver import assets as silver_assets

# Ensure tables exist when Dagster starts
init_db()

all_assets = load_assets_from_modules([bronze_assets, silver_assets, gold_assets])
all_asset_checks = load_asset_checks_from_modules([asset_checks])
materialize_all = define_asset_job("carms_job", selection="*")

defs = Definitions(assets=all_assets, asset_checks=all_asset_checks, jobs=[materialize_all])

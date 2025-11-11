#!/usr/bin/env python3

import logging
import tempfile
from pathlib import Path

import polars as pl
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://raw.githubusercontent.com/cdisc-org/sdtm-adam-pilot-project/master/updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01"

SDTM_DATASETS = [
    "ae",
    "cm",
    "dm",
    "ds",
    "ex",
    "lb",
    "mh",
    "qs",
    "relrec",
    "sc",
    "se",
    "suppae",
    "suppdm",
    "suppds",
    "supplb",
    "sv",
    "ta",
    "te",
    "ti",
    "ts",
    "tv",
    "vs",
]

ADAM_DATASETS = [
    "adae",
    "adlbc",
    "adlbh",
    "adlbhy",
    "adqsadas",
    "adqscibc",
    "adqsnpix",
    "adsl",
    "adtte",
    "advs",
]


def create_directories():
    """Create directory structure for data storage"""
    dirs = [Path("data/sdtm"), Path("data/adam")]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")


def download_xpt_file(url: str) -> pl.DataFrame:
    """Download XPT file and convert to polars DataFrame with all columns as strings"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Save to temporary file first as polars needs a file path for SAS files
        with tempfile.NamedTemporaryFile(suffix=".xpt", delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name

        # Read XPT file with polars
        try:
            import pandas as pd

            # Use pandas to read SAS then convert to polars
            df_pandas = pd.read_sas(tmp_path, format="xport")

            # Convert all columns to string type
            df_pandas = df_pandas.astype(str)

            # Replace 'nan' strings with empty strings for better handling
            df_pandas = df_pandas.replace("nan", "")

            df = pl.from_pandas(df_pandas)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

        return df
    except Exception as e:
        logger.error(f"Error downloading/reading {url}: {e}")
        return None


def process_sdtm_data():
    """Download and convert SDTM datasets to parquet"""
    logger.info("Processing SDTM datasets...")

    for dataset in SDTM_DATASETS:
        url = f"{BASE_URL}/tabulations/sdtm/{dataset}.xpt"
        logger.info(f"Downloading SDTM dataset: {dataset}")

        df = download_xpt_file(url)
        if df is not None:
            output_path = Path(f"data/sdtm/{dataset}.parquet")
            df.write_parquet(output_path)
            logger.info(f"Saved {dataset} to {output_path} ({len(df)} rows)")
        else:
            logger.warning(f"Skipped {dataset} due to download error")


def process_adam_data():
    """Download and convert ADaM datasets to parquet"""
    logger.info("Processing ADaM datasets...")

    for dataset in ADAM_DATASETS:
        url = f"{BASE_URL}/analysis/adam/datasets/{dataset}.xpt"
        logger.info(f"Downloading ADaM dataset: {dataset}")

        df = download_xpt_file(url)
        if df is not None:
            output_path = Path(f"data/adam/{dataset}.parquet")
            df.write_parquet(output_path)
            logger.info(f"Saved {dataset} to {output_path} ({len(df)} rows)")
        else:
            logger.warning(f"Skipped {dataset} due to download error")


def verify_data():
    """Verify that all expected files were created"""
    logger.info("\nVerifying downloaded data...")

    sdtm_files = list(Path("data/sdtm").glob("*.parquet"))
    adam_files = list(Path("data/adam").glob("*.parquet"))

    logger.info(f"SDTM files created: {len(sdtm_files)}/{len(SDTM_DATASETS)}")
    logger.info(f"ADaM files created: {len(adam_files)}/{len(ADAM_DATASETS)}")

    # Check for missing files
    sdtm_created = {f.stem for f in sdtm_files}
    adam_created = {f.stem for f in adam_files}

    missing_sdtm = set(SDTM_DATASETS) - sdtm_created
    missing_adam = set(ADAM_DATASETS) - adam_created

    if missing_sdtm:
        logger.warning(f"Missing SDTM datasets: {missing_sdtm}")
    if missing_adam:
        logger.warning(f"Missing ADaM datasets: {missing_adam}")

    return len(missing_sdtm) == 0 and len(missing_adam) == 0


def main():
    """Main function to orchestrate data preparation"""
    logger.info("Starting CDISC Pilot Data Preparation")
    logger.info("=" * 50)

    # Create directory structure
    create_directories()

    # Process SDTM data
    process_sdtm_data()

    # Process ADaM data
    process_adam_data()

    # Verify results
    success = verify_data()

    if success:
        logger.info(
            "\n[SUCCESS] All datasets successfully downloaded and converted to parquet format!"
        )
    else:
        logger.warning(
            "\n[WARNING] Some datasets could not be downloaded. Please check the logs above."
        )

    logger.info("\nData organization:")
    logger.info("  SDTM data: data/sdtm/")
    logger.info("  ADaM data: data/adam/")


if __name__ == "__main__":
    main()

import polars as pl

def get_bmi(height: pl.Series, weight: pl.Series) -> pl.Series:

    # Convert height from cm to m
    height_m = height / 100
    
    # Calculate BMI
    bmi = weight / (height_m ** 2)
    
    return bmi
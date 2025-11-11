#!/usr/bin/env python3
"""
Generate ADSL dataset using the ADaM YAML system
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Generate ADSL dataset"""
    print("Generating ADSL Dataset")
    print("=" * 50)

    try:
        from src.adamyaml.adam_derivation import AdamDerivation

        # Initialize the derivation engine
        spec_path = "spec/study1/adsl_study1.yaml"
        print(f"Loading specification: {spec_path}")

        engine = AdamDerivation(spec_path)
        print("+ Engine initialized")

        # Generate the dataset
        print("Building ADSL dataset...")
        df = engine.build()

        print(f"+ Dataset created: {df.shape}")
        print(f"Columns: {list(df.columns)}")

        # Show sample data
        print("\nSample data:")
        print(df.head(3))

        # Save the dataset
        output_path = engine.save()
        print(f"+ Dataset saved to: {output_path}")

        return True

    except Exception as e:
        print(f"ERROR: Error generating ADSL: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\nSUCCESS: ADSL generation completed successfully!")
    else:
        print("\nFAILED: ADSL generation failed. Check the error messages above.")

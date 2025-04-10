import pandas as pd

def filter_by_lexile(input_file, output_file):
    # Read the file into a DataFrame
    # The exact read function depends on your file type
    # For CSV:
    df = pd.read_csv(input_file)
    # For Excel:
    # df = pd.read_excel(input_file)
    
    # Filter to keep only rows where lexile column is not empty
    # This will keep rows where lexile is not NaN, not empty string, etc.
    filtered_df = df[df['lexile'].notna() & (df['lexile'] != '')]
    
    # Save to a new file
    # For CSV:
    filtered_df.to_csv(output_file, index=False)
    # For Excel:
    # filtered_df.to_excel(output_file, index=False)
    
    # Print some stats
    print(f"Original file had {len(df)} rows")
    print(f"Filtered file has {len(filtered_df)} rows")
    print(f"Removed {len(df) - len(filtered_df)} rows")

# Example usage
input_file = "allwords.csv"  # Replace with your file path
output_file = "only_lexile_all_columns.csv"  # Replace with desired output path

filter_by_lexile(input_file, output_file)
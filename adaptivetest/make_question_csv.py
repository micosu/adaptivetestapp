import pandas as pd
import numpy as np
import math

def compute_irt_params(word_attrs, min_log_freq, max_log_freq):
    """
    Compute IRT parameters (a, b, c) for a word based on its attributes.
    
    Parameters:
    - word_attrs: Dictionary containing word attributes
    - min_log_freq, max_log_freq: Min and max log frequencies for normalization
    
    Returns:
    - a: Discrimination parameter
    - b: Difficulty parameter
    - c: Guessing parameter
    """
    # Get word for debugging
    word = word_attrs.get('word', 'unknown')
    
    # Handle age of acquisition - primary factor for difficulty
    if pd.isna(word_attrs['age_of_acq']) or word_attrs['age_of_acq'] is None:
        age_centered = 0  # Neutral value if age is missing
    else:
        # Normalize age to create more headroom for advanced words
        # Center around age 9 and compress the scale
        age = word_attrs['age_of_acq']
        age_centered = (age - 9) / 3  # More gradual scaling
    
    # Process lexile as secondary factor
    if pd.isna(word_attrs['lexile']) or word_attrs['lexile'] is None:
        lexile_factor = 0  # Neutral value if lexile is missing
    else:
        # Create a much more gradual lexile scale
        lexile = word_attrs['lexile']
        # Use log scale with stronger dampening
        lexile_factor = math.log10(lexile / 500) * 0.8  # Heavily dampened
    
    # Process word frequency (gen_freq) as a major factor in difficulty
    try:
        if pd.isna(word_attrs['gen_freq']) or word_attrs['gen_freq'] is None:
            freq_factor = 0
        else:
            # Log transform and invert so higher frequency = lower difficulty
            freq = max(1, word_attrs['gen_freq'])  # Ensure positive
            log_freq = math.log10(freq)
            
            # Normalize to a reasonable range (-1.5 to 1.5)
            # Higher frequency (common) words have negative contribution to difficulty
            freq_range = max_log_freq - min_log_freq
            if freq_range > 0:
                norm_freq = (log_freq - min_log_freq) / freq_range
                freq_factor = -2 * norm_freq + 1  # Map from -1 to 1
            else:
                freq_factor = 0
    except (TypeError, ValueError, KeyError, ZeroDivisionError):
        freq_factor = 0
    
    # Calculate difficulty (b) with rebalanced weights
    # Age of acquisition: 40%, frequency: 40%, lexile: 20%
    raw_b = 0.4 * age_centered + 0.4 * freq_factor + 0.2 * lexile_factor
    
    # Apply a very gentle sigmoid to ensure we have room at the top
    # This version only compresses values that are already near the extremes
    if raw_b > 0:
        b = 3 * math.tanh(raw_b * 0.7)  # Tanh approaches ±1 asymptotically
    else:
        b = 3 * math.tanh(raw_b * 0.7)
        
    # Debug output
    print(f"Word: {word}, Age: {word_attrs.get('age_of_acq', 'N/A')}, "
          f"Lexile: {word_attrs.get('lexile', 'N/A')}, "
          f"Freq: {word_attrs.get('gen_freq', 'N/A')}, "
          f"b: {b:.2f} "
          f"(age_factor: {age_centered:.2f}, freq_factor: {freq_factor:.2f}, lexile_factor: {lexile_factor:.2f})")
    
    # Calculate discrimination (a) - with error handling
    try:
        if pd.isna(word_attrs['syllables']) or word_attrs['syllables'] is None:
            syllable_factor = 0
        else:
            syllable_factor = (3 - word_attrs['syllables']) / 3
            
        if pd.isna(word_attrs['fiction_rank']) or word_attrs['fiction_rank'] is None:
            rank_factor = 0
        else:
            rank_factor = (math.log10(word_attrs['fiction_rank'] + 1) - 3) / 2
            
        a = 1.0 + 0.4 * (syllable_factor + rank_factor)
    except (TypeError, ValueError, KeyError):
        a = 1.0  # Default value if calculation fails
        
    a = max(0.5, min(a, 2.0))  # Constrain to reasonable range

    # Calculate guessing (c) - with error handling
    try:
        if pd.isna(word_attrs['gen_freq']) or word_attrs['gen_freq'] is None:
            norm_freq = 0.5  # Moderate value if frequency is missing
        else:
            norm_freq = (math.log(word_attrs['gen_freq'] + 1) - min_log_freq) / (max_log_freq - min_log_freq)
            norm_freq = max(0, min(norm_freq, 1))  # Ensure it's within 0-1 range
    except (TypeError, ValueError, KeyError, ZeroDivisionError):
        norm_freq = 0.5  # Default value if calculation fails
        
    c = 0.2 + 0.15 * norm_freq
    c = max(0.2, min(c, 0.35))

    return a, b, c

def main():
    import argparse
    import os
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Merge word attributes with questions and compute IRT parameters')
    parser.add_argument('--words', dest='words_file', default="only_lexile_all_columns.csv", help='Path to lexile file')
    parser.add_argument('--questions', dest='questions_file', default="words.csv", help='Path to questions file')
    parser.add_argument('--output', dest='output_file', default="improved_question_bank.csv", help='Path to question bank')
    args = parser.parse_args()
    
    # File paths
    words_file = args.words_file
    questions_file = args.questions_file
    output_file = args.output_file
    
    # Verify input files exist
    for file_path in [words_file, questions_file]:
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' does not exist.")
            return
    
    # Load the CSV files with error handling
    try:
        print(f"Loading {words_file}...")
        words_df = pd.read_csv(words_file)
        
        # Check for required columns in words_df
        required_word_cols = ['word_id', 'word', 'age_of_acq', 'lexile', 'word_grade', 
                             'syllables', 'fiction_rank', 'gen_freq']
        missing_cols = [col for col in required_word_cols if col not in words_df.columns]
        if missing_cols:
            print(f"Error: Missing required columns in {words_file}: {missing_cols}")
            return
    except Exception as e:
        print(f"Error loading {words_file}: {e}")
        return
    
    try:
        print(f"Loading {questions_file}...")
        questions_df = pd.read_csv(questions_file)
        
        # Check for required columns in questions_df
        required_question_cols = ['word', 'word_id', 'choices', 'correct_answer']
        
        # Special handling if we need to find a column with word_id info
        if 'word_id' not in questions_df.columns and 'word' not in questions_df.columns:
            print("Warning: Neither 'word_id' nor 'word' columns found in questions file.")
            print("Will attempt to find a column that might contain word ID information...")
            
            # Look for columns that might contain "word" and "id" in their names
            potential_cols = [col for col in questions_df.columns if 'word' in col.lower() and ('id' in col.lower() or 'text' in col.lower())]
            if potential_cols:
                print(f"Found potential word ID columns: {potential_cols}")
            else:
                print("No potential word ID columns found. Computation may fail.")
                
        # Check for other required columns
        current_cols = list(questions_df.columns)
        missing_cols = [col for col in required_question_cols if col not in current_cols]
        if missing_cols:
            print(f"Error: Missing required columns in {questions_file}: {missing_cols}")
            return
    except Exception as e:
        print(f"Error loading {questions_file}: {e}")
        return
    
    # Calculate min and max log frequencies for normalization
    min_log_freq = math.log(words_df['gen_freq'].min() + 1)
    max_log_freq = math.log(words_df['gen_freq'].max() + 1)
    
    print(f"Min log freq: {min_log_freq}, Max log freq: {max_log_freq}")
    
    # Create a dictionary mapping word_id to the row in words_df
    # Convert all word_id values to strings to ensure consistent matching
    word_dict = {str(row['word_id']): row for _, row in words_df.iterrows()}
    
    # Create empty lists for the IRT parameters
    text = []
    discriminations = []
    difficulties = []
    guessings = []
    
    # Process each question
    print("Computing IRT parameters for each question...")
    for _, question_row in questions_df.iterrows():
        # Check if word_id column exists
        if 'word_id' not in question_row:
            # Try using word column to match with words_df
            if 'word' in question_row and question_row['word'] in words_df['word'].values:
                word_row = words_df[words_df['word'] == question_row['word']].iloc[0]
                word_attrs = word_row
                word_id = word_row['word_id']
            else:
                print(f"Warning: Cannot find matching word for row {_}. Using default values.")
                a, b, c = 1.0, 0.0, 0.25  # Default values
                discriminations.append(a)
                difficulties.append(b)
                guessings.append(c)
                continue
        else:
            word_id = question_row['word_id']
            
            # Convert word_id to string if it's not already
            if not isinstance(word_id, str):
                word_id = str(word_id)
        
        if word_id in word_dict:
            word_attrs = word_dict[word_id]
            a, b, c = compute_irt_params(word_attrs, min_log_freq, max_log_freq)
            print(f"Word: {word_attrs['word']}, Grade: {word_attrs['word_grade']}, "
                  f"IRT params: a={a:.2f}, b={b:.2f}, c={c:.2f}")
        else:
            print(f"Warning: word_id {word_id} not found in words file. Using default values.")
            a, b, c = 1.0, 0.0, 0.25  # Default values
            
        discriminations.append(a)
        difficulties.append(b)
        guessings.append(c)
        text.append(f"Choose the word that has a similar meaning to {question_row['word'].upper()}")
    
    # Add the computed parameters to the questions dataframe
    questions_df['discrimination'] = discriminations
    questions_df['difficulty'] = difficulties
    questions_df['guessing'] = guessings
    questions_df['text'] = text
    
    # Select only the required columns for the output
    output_df = questions_df[['text', 'choices', 'correct_answer', 
                             'discrimination', 'difficulty', 'guessing']]
    
    # Write the output to a new CSV file
    print(f"Writing output to {output_file}...")
    output_df.to_csv(output_file, index=False)
    
    print(f"Done! Created {output_file} with {len(output_df)} rows.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3

import os
import re
import sys
import pandas as pd
import argparse
from collections import defaultdict
import csv
import time
from pathlib import Path
from typing import List, Tuple

def get_result_files() -> List[Tuple[Path, float]]:
    """Get list of CSV files from results directory and subdirectories sorted by modification time."""
    results_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'results'
    if not results_dir.exists():
        print(f"Error: Results directory not found at {results_dir}", file=sys.stderr)
        sys.exit(1)
        
    # Recursively find all CSV files in results directory and subdirectories
    files = []
    for root, _, filenames in os.walk(results_dir):
        for filename in filenames:
            if filename.endswith('.csv'):
                file_path = Path(root) / filename
                files.append((file_path, file_path.stat().st_mtime))
    
    return sorted(files, key=lambda x: x[1], reverse=True)

def select_result_file() -> Path:
    """Display last 3 result files and let user select one."""
    files = get_result_files()
    if not files:
        print("Error: No CSV files found in results directory", file=sys.stderr)
        sys.exit(1)
        
    print("\nAvailable result files (last 3):", file=sys.stderr)
    for i, (file, mtime) in enumerate(files[:3], 1):
        print(f"{i}. {file.relative_to(file.parent.parent.parent)} (modified: {time.ctime(mtime)})", file=sys.stderr)
        
    while True:
        try:
            choice = input("\nSelect a file (1-3): ")
            idx = int(choice) - 1
            if 0 <= idx < min(3, len(files)):
                return files[idx][0]
            print("Invalid choice. Please select a number between 1 and 3", file=sys.stderr)
        except ValueError:
            print("Invalid input. Please enter a number", file=sys.stderr)

def extract_answer(row, relaxed):
    # Extract the answer from the model's response.
    if type(row['model_response']) is not str:
        return 0

    # Try to find the answer using the primary regex pattern.
    matches = re.findall(r'<ANSWER>([0-9])</ANSWER>', row['model_response'])
    if matches:
        return int(matches[0])

    # If the primary pattern fails and relaxed mode is enabled, try alternative patterns.
    if relaxed:
        relaxed_answer_regexes = [
            r'boxed\{([0-9])\}',
            r'</ANSWER>([0-9])</ANSWER>',
            r'ANSWER: ?([0-9])',
            r'\*\*ANSWER\*\*:? ?([0-9])',
            r'\*\*ANSWER>\*\*([0-9])</ANSWER>',
        ]
        for relaxed_answer_regex in relaxed_answer_regexes:
            matches = re.findall(relaxed_answer_regex, row['model_response'])
            if matches:
                return int(matches[0])

    # Return 0 if no answer is found.
    return 0

# Set up the argument parser to handle command-line options.
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--csv", help="Generate CSV output.", action="store_true")
parser.add_argument("-r", "--relaxed", help="Relaxed answer format requirements", action="store_true")
parser.add_argument("-d", "--detailed", help="Generate detailed output", action="store_true")
args = parser.parse_args()

gen_csv = args.csv
is_output_detailed = args.detailed
is_answer_relaxed = args.relaxed

# Let user select result file
result_file = select_result_file()
print(f"\nUsing result file: {result_file}", file=sys.stderr)

# Create data directory with same structure as results
data_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'data'
relative_path = result_file.relative_to(result_file.parent.parent.parent)
output_dir = data_dir / relative_path.parent
os.makedirs(output_dir, exist_ok=True)

# Prepare output file name
output_file = output_dir / f"metrics_{result_file.name}"
print(f"Output will be saved to: {output_file}", file=sys.stderr)

# Read the CSV data from selected file
df = pd.read_csv(result_file, names=['problem_size', 'relation_name', 'correct_answer', 'quiz', 'model_name', 'provider_name', 'reasoning_effort', 'system_prompt', 'model_response'], dtype={'problem_size': 'int32', 'relation_name': 'object', 'correct_answer': 'int32', 'quiz': 'object', 'model_name': 'object', 'provider_name': 'object', 'reasoning_effort': 'object', 'system_prompt': 'object', 'model_response': 'object'})

# Extract the model's answer and determine if it's correct or missing.
df['model_answer'] = df.apply(extract_answer, axis=1, args=(is_answer_relaxed,))
df['answer_correct'] = df['correct_answer'] == df['model_answer']
df['answer_incorrect'] = (df['correct_answer'] != df['model_answer']) & (0 != df['model_answer'])
df['answer_missing'] = 0 == df['model_answer']

# Select relevant columns for further processing.
df = df[['problem_size', 'relation_name', 'model_name', 'answer_correct', 'answer_incorrect', 'answer_missing']]

# Group and aggregate data based on the output detail level.
if is_output_detailed:
    # Detailed output: Sum correct, incorrect, and missing answers.
    df = df.groupby(['problem_size', 'relation_name', 'model_name'])[['answer_correct', 'answer_incorrect', 'answer_missing']].sum().reset_index()
else:
    # Condensed output: Calculate the percentage of correct answers.
    df = df.groupby(['problem_size', 'relation_name', 'model_name'])['answer_correct'].mean().reset_index().rename(columns={'answer_correct': 'percent_correct'})

    # Pivot the table to have relation names as columns.
    df = df.pivot(index=['problem_size', 'model_name'], columns='relation_name', values='percent_correct').reset_index()

    # Calculate the average lineage score across different relation types.
    df['lineage'] = df[['ANCESTOR', 'DESCENDANT', 'COMMON_ANCESTOR', 'COMMON_DESCENDANT']].mean(axis=1)

    # Select relevant columns and pivot again for problem sizes.
    df = df[['problem_size', 'model_name', 'lineage']]
    df = df.pivot(index=['model_name'], columns='problem_size', values='lineage').fillna(0).reset_index()

    # Get available problem sizes from the data
    problem_sizes = sorted(df.columns.drop('model_name').astype(int).tolist())
    if not problem_sizes:
        print("Error: No valid problem sizes found in data", file=sys.stderr)
        sys.exit(1)

    # Calculate the overall lineage score across available sizes
    df['lineage'] = df[problem_sizes].mean(axis=1)

    # Rename columns to include problem size in the name
    df = df[['model_name', 'lineage'] + problem_sizes]
    df = df.rename(columns={size: f'lineage-{size}' for size in problem_sizes})

    if len(problem_sizes) == 1:
        print(f"\nProcessing single problem size: {problem_sizes[0]}", file=sys.stderr)

    # Sort by lineage score and calculate rank.
    df = df.sort_values(['lineage'], ascending=False)
    df['Nr'] = df['lineage'].rank(method='min', ascending=False).astype('int32')

    # Select final columns for output.
    df = df[['Nr', 'model_name', 'lineage'] + [f'lineage-{size}' for size in problem_sizes]]

# Generate output in the specified format
output_data = df.to_csv(index=False) if gen_csv else df.to_markdown(floatfmt=".3f", index=False)

# Write to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(output_data)

# Also print to stdout for piping
print(output_data)

print(f"\nMetrics saved to: {output_file}", file=sys.stderr)

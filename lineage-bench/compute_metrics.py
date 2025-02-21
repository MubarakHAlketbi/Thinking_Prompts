#!/usr/bin/env python3

import os
import re
import sys
import pandas as pd
import argparse
from collections import defaultdict
import csv

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

# Read the CSV data from standard input.
df = pd.read_csv(sys.stdin, names=['problem_size', 'relation_name', 'correct_answer', 'quiz', 'model_name', 'provider_name', 'reasoning_effort', 'system_prompt', 'model_response'], dtype={'problem_size': 'int32', 'relation_name': 'object', 'correct_answer': 'int32', 'quiz': 'object', 'model_name': 'object', 'provider_name': 'object', 'reasoning_effort': 'object', 'system_prompt': 'object', 'model_response': 'object'})

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

    problem_sizes = [8, 16, 32, 64]

    # Calculate the overall lineage score across problem sizes.
    df['lineage'] = df[problem_sizes].mean(axis=1)

    # Rename columns to include problem size in the name.
    df = df[['model_name', 'lineage'] + problem_sizes]
    df = df.rename(columns={ size: f'lineage-{size}' for size in problem_sizes })

    # Sort by lineage score and calculate rank.
    df = df.sort_values(['lineage'], ascending=False)
    df['Nr'] = df['lineage'].rank(method='min', ascending=False).astype('int32')

    # Select final columns for output.
    df = df[['Nr', 'model_name', 'lineage'] + [f'lineage-{size}' for size in problem_sizes]]

# Print the output in the specified format (CSV or Markdown).
if gen_csv:
    print(df.to_csv(index=False))
else:
    print(df.to_markdown(floatfmt=".3f", index=False))

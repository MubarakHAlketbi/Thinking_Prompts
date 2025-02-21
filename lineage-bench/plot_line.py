#!/usr/bin/env python3

import sys
import argparse
import matplotlib.ticker as tck
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Set up the argument parser to handle the output file option.
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", help="Write rendered plot to this file.")
args = parser.parse_args()

output_file = args.output

# Read the CSV data from standard input.
df = pd.read_csv(sys.stdin)

# Extract column names and problem sizes.
col_names = df.columns[3:].values
problem_sizes = list(map(lambda c: int(c.removeprefix('lineage-')), col_names))

# Plot the data.
plt.figure(figsize=(12, 8))

# Set up a colormap for the lines.
colormap = plt.cm.nipy_spectral
colors = colormap(np.linspace(0, 1, len(df['model_name'])))
plt.gca().set_prop_cycle('color', colors)

# Plot each model's performance across problem sizes.
for index, row in df.iterrows():
    plt.plot(problem_sizes, row[col_names], marker='o', label=row['model_name'])

# Customize the plot (title, labels, legend, scale, ticks, grid).
plt.title('Lineage benchmark scores for different problem sizes.')
plt.xlabel('Problem Size')
plt.ylabel('Lineage Score')
plt.legend(title='Model Name', loc='upper right')
plt.xscale('log')
plt.gca().get_xaxis().set_minor_locator(tck.AutoMinorLocator())
plt.xticks([8, 16, 32, 64])
plt.gca().get_xaxis().set_major_formatter(tck.ScalarFormatter())
plt.grid(True)
plt.tight_layout()

# Save the plot to a file if specified.
if output_file:
    plt.savefig(output_file)

# Show the plot.
plt.show()

# Lineage Bench Documentation

This document provides a detailed explanation of the code in the `lineage-bench` directory.

## Overview

The `lineage-bench` project is designed to test LLM reasoning abilities using lineage relationship quizzes. It generates quizzes, tests models using the OpenRouter API, computes metrics, and visualizes the results.

## Files

The project consists of the following Python scripts:

1.  **`lineage_bench.py`:** Generates lineage relationship quizzes.
2.  **`run_openrouter.py`:** Tests LLM models using the OpenRouter API.
3.  **`compute_metrics.py`:** Calculates benchmark results.
4.  **`plot_line.py`:** Generates a line plot of the results.
5.  **`plot_stacked.py`:** Generates a stacked bar plot of the results.

### 1. `lineage_bench.py`

**Purpose:** Generates lineage relationship quizzes of varying difficulty.

**Usage:**

```bash
./lineage_bench.py -l LENGTH [-p PROMPT] [-s] [-n NUMBER] [-r SEED]
```

**Arguments:**

*   `-l LENGTH`, `--length LENGTH`: Number of people in the quiz (required).
*   `-p PROMPT`, `--prompt PROMPT`: Prompt template (default provided).
*   `-s`, `--shuffle`: Shuffle the order of lineage relations.
*   `-n NUMBER`, `--number NUMBER`: Number of quizzes per answer type (default: 10).
*   `-r SEED`, `--seed SEED`: Random seed for reproducibility.

**Functionality:**

1.  **`generate_quiz(length, quiz_type, shuffle=False, prompt=DEFAULT_PROMPT)`:**
    *   Generates a single quiz.
    *   `length`: Number of people.
    *   `quiz_type`: Type of quiz (ANCESTOR, DESCENDANT, COMMON_ANCESTOR, COMMON_DESCENDANT).
    *   `shuffle`: Whether to shuffle relations.
    *   `prompt`: Prompt template.
    *   Creates a list of character names.
    *   Generates ancestor relations based on `quiz_type`.
    *   Constructs the quiz string (relations, question, answers).
    *   Returns the quiz string and the correct answer number.

2.  **`generate_quizzes(length, num_quizzes=10, prompt=DEFAULT_PROMPT, shuffle=False, seed=None)`:**
    *   Generates multiple quizzes of all types.
    *   `length`: Number of people.
    *   `num_quizzes`: Number of quizzes per type.
    *   `prompt`: Prompt template.
    *   `shuffle`: Whether to shuffle relations.
    *   `seed`: Random seed.
    *   Yields tuples of (relation type, correct answer, quiz string).

3.  **`if __name__ == '__main__':`:**
    *   Parses command-line arguments.
    *   Calls `generate_quizzes` and writes the output to a CSV file in the 'tests' directory.
    *   File name includes timestamp for tracking.

### 2. `run_openrouter.py`

**Purpose:** Tests LLM models using the OpenRouter API.

**Usage:**

```bash
./run_openrouter.py -m MODEL [-p PROVIDER] [-e EFFORT] [-t THREADS] [-v] [-s [SYSTEM_PROMPT]] [--referer REFERER] [--title TITLE] [-f FALLBACKS] [--data-privacy DATA_PRIVACY] [--require-params] [--quantization LEVEL] [--ignore-providers PROVIDERS] [--fallback-models MODELS]
```

**Arguments:**

*   `-m MODEL`, `--model MODEL`: OpenRouter model name (required). Defaults to `openrouter/auto` if not provided.
*   `-p PROVIDER`, `--provider PROVIDER`: Comma separated OpenRouter provider name(s).
*   `-e EFFORT`, `--effort EFFORT`: Reasoning effort (o1 model only).
*   `-t THREADS`, `--threads THREADS`: Number of threads (default: 8).
*   `-v`, `--verbose`: Enable verbose output.
*   `-s [SYSTEM_PROMPT]`, `--system-prompt [SYSTEM_PROMPT]`: System prompt.
*   `--referer REFERER`: Site URL for OpenRouter rankings.
*   `--title TITLE`: Site title for OpenRouter rankings.
*   `-f FALLBACKS`, `--fallbacks FALLBACKS`: Allow fallbacks (default: True).
*   `--data-privacy DATA_PRIVACY`: Data collection preference ('allow' or 'deny').
*   `--require-params`: Only use providers that support all parameters.
*   `--quantization LEVEL`: Filter providers by quantization level (int4, int8, fp6, fp8, fp16, bf16, fp32).
*   `--ignore-providers PROVIDERS`: Comma-separated list of providers to ignore.
*   `--fallback-models MODELS`: Comma-separated list of fallback models to try if primary model fails.

**Functionality:**

1.  **`get_test_files()`:** Lists CSV files from tests directory sorted by modification time.
2.  **`select_test_file()`:** Displays last 3 test files and lets user select one.
3.  **`get_system_prompt(prompt_arg)`:** Reads system prompt from file or uses the provided string.
4.  **`make_request(row)`:**
    *   Sends a single quiz to the OpenRouter API.
    *   Constructs the request payload (model, messages, provider preferences).
    *   Handles API errors (rate limits, quota exceeded, invalid key, etc.) with retries and exponential backoff.
    *   Returns the results.
5.  **Main execution:**
    *   Parses command-line arguments.
    *   Lets user select a test file from the 'tests' directory.
    *   Uses a `ThreadPoolExecutor` to make requests concurrently.
    *   Writes results to both:
        - stdout (for piping to compute_metrics.py)
        - A file in 'results' directory with same name as input file

### 3. `compute_metrics.py`

**Purpose:** Calculates benchmark results from the model responses.

**Usage:**

```bash
./compute_metrics.py [-c] [-r] [-d]
```

**Arguments:**

*   `-c`, `--csv`: Generate CSV output.
*   `-r`, `--relaxed`: Relaxed answer format requirements.
*   `-d`, `--detailed`: Generate detailed output.

**Functionality:**

1.  **`extract_answer(row, relaxed)`:** Extracts the model's answer from the response string, handling different answer formats.
2.  **Main execution:**
    *   Reads data from stdin (CSV format).
    *   Extracts the model's answer using `extract_answer`.
    *   Calculates correctness (correct, incorrect, missing).
    *   Groups and aggregates the results based on problem size, relation name, and model name.
    *   Calculates the overall lineage score.
    *   Outputs the results in either CSV or Markdown format.

### 4. `plot_line.py`

**Purpose:** Generates a line plot of the benchmark results.

**Usage:**

```bash
./plot_line.py [-o OUTPUT]
```

**Arguments:**

*   `-o OUTPUT`, `--output OUTPUT`: Output file for the plot.

**Functionality:**

1.  Reads data from stdin (CSV format).
2.  Plots lineage scores for different problem sizes, with a separate line for each model.
3.  Customizes the plot (title, labels, legend, x-axis scale, grid).
4.  Saves the plot to a file (if specified) or displays it.

### 5. `plot_stacked.py`

**Purpose:** Generates a stacked bar plot of the benchmark results.

**Usage:**

```bash
./plot_stacked.py [-o OUTPUT]
```

**Arguments:**

*   `-o OUTPUT`, `--output OUTPUT`: Output file for the plot.

**Functionality:**

1.  Reads data from stdin (CSV format).
2.  Creates a stacked horizontal bar chart, showing the breakdown of scores for different problem sizes for each model.
3.  Customizes the plot (labels, title, legend, grid).
4.  Saves the plot to a file (if specified) or displays it.

## Project Structure and Workflow

The project uses a structured directory system for managing test files and results:

### Directories

* **`tests/`**: Contains generated quiz files from lineage_bench.py
  - Files are named with timestamps for tracking
  - Used as input for run_openrouter.py

* **`results/`**: Contains model test results from run_openrouter.py
  - Files maintain same names as their corresponding test files
  - Used for analysis and visualization

### Typical Workflow

1. **Generate Tests:**
   ```bash
   ./lineage_bench.py -l 8
   ```
   - Creates a timestamped CSV file in tests/
   - Contains lineage relationship quizzes

2. **Run Model Tests:**
   ```bash
   ./run_openrouter.py -m "openai/gpt-4"
   ```
   - Shows last 3 test files for selection
   - Runs tests using selected file
   - Saves results to results/ directory
   - Also outputs to stdout for piping

3. **Analyze Results:**
   ```bash
   ./run_openrouter.py -m "openai/gpt-4" | ./compute_metrics.py
   ```
   - Processes model responses
   - Calculates accuracy metrics
   - Can be piped to plotting tools

4. **Visualize Results:**
   ```bash
   ./compute_metrics.py -c < results/test_file.csv | ./plot_line.py
   ```
   - Creates visualizations from results
   - Can use either line or stacked plots
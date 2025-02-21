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
    *   File name format: `{length}_{date}_{time}.csv` (e.g., `8_20250221_0401.csv`).

### 2. `run_openrouter.py`

**Purpose:** Tests LLM models using the OpenRouter API.

**Configuration:**

The script can be configured through both environment variables and command-line arguments. Command-line arguments take precedence over environment variables.

1. **Environment Variables** (in .env file):
   ```bash
   # API Configuration
   OPENROUTER_API_KEY=your_api_key_here
   
   # Model and Provider Settings
   OPENROUTER_MODEL=openrouter/auto
   OPENROUTER_PROVIDER=OpenAI,Anthropic
   OPENROUTER_EFFORT=medium
   OPENROUTER_THREADS=8
   
   # System Prompt (use either SYSTEM_PROMPT or SYSTEM_PROMPT_FILE)
   OPENROUTER_SYSTEM_PROMPT="Your prompt here..."
   OPENROUTER_SYSTEM_PROMPT_FILE=prompts/system_prompt.md
   
   # OpenRouter Rankings
   OPENROUTER_REFERER=https://your-site.com
   OPENROUTER_TITLE=Your Site Name
   
   # Provider Options
   OPENROUTER_FALLBACKS=true
   OPENROUTER_DATA_PRIVACY=deny
   OPENROUTER_REQUIRE_PARAMS=false
   OPENROUTER_QUANTIZATION=fp16
   OPENROUTER_IGNORE_PROVIDERS=Azure,DeepInfra
   OPENROUTER_FALLBACK_MODELS=anthropic/claude-3-sonnet,openai/gpt-3.5-turbo
   ```

2. **Command-Line Arguments:**
   ```bash
   ./run_openrouter.py [-m MODEL] [-p PROVIDER] [-e EFFORT] [-t THREADS] [-v] [-s SYSTEM_PROMPT] [--referer REFERER] [--title TITLE] [-f FALLBACKS] [--data-privacy DATA_PRIVACY] [--require-params] [--quantization LEVEL] [--ignore-providers PROVIDERS] [--fallback-models MODELS]
   ```

**Arguments:**

*   `-m MODEL`, `--model MODEL`: OpenRouter model name. Defaults to value from OPENROUTER_MODEL or 'openrouter/auto'.
*   `-p PROVIDER`, `--provider PROVIDER`: Comma separated OpenRouter provider name(s).
*   `-e EFFORT`, `--effort EFFORT`: Reasoning effort (o1 model only).
*   `-t THREADS`, `--threads THREADS`: Number of threads (default from OPENROUTER_THREADS or 8).
*   `-v`, `--verbose`: Enable verbose output (shows full configuration).
*   `-s SYSTEM_PROMPT`, `--system-prompt SYSTEM_PROMPT`: System prompt text or file path (.txt/.md).
*   `--referer REFERER`: Site URL for rankings on openrouter.ai.
*   `--title TITLE`: Site title for rankings on openrouter.ai.
*   `-f FALLBACKS`, `--fallbacks FALLBACKS`: Allow fallbacks (default from OPENROUTER_FALLBACKS or true).
*   `--data-privacy DATA_PRIVACY`: Data collection preference ('allow' or 'deny').
*   `--require-params`: Only use providers that support all parameters.
*   `--quantization LEVEL`: Filter providers by quantization level (int4, int8, fp6, fp8, fp16, bf16, fp32).
*   `--ignore-providers PROVIDERS`: Comma-separated list of providers to ignore.
*   `--fallback-models MODELS`: Comma-separated list of fallback models to try if primary model fails.

**Functionality:**

1.  **`get_env_defaults()`:**
    * Reads configuration defaults from environment variables
    * Handles all supported settings (model, provider, threads, etc.)
    * Provides fallback values when variables are not set

2.  **`get_test_files()`:**
    * Lists CSV files from tests directory sorted by modification time
    * Returns list of (file, modification_time) tuples

3.  **`select_test_file()`:**
    * Displays last 3 test files and lets user select one
    * Shows modification times for each file
    * Validates user input

4.  **`get_system_prompt(prompt_arg)`:**
    * Supports multiple prompt sources:
      - Direct text input
      - File path (.txt or .md)
      - Environment variables (OPENROUTER_SYSTEM_PROMPT or OPENROUTER_SYSTEM_PROMPT_FILE)
    * Includes error handling for file reading
    * Falls back to default prompt if needed

5.  **`make_request(row)`:**
    * Sends a single quiz to the OpenRouter API
    * Constructs the request payload (model, messages, provider preferences)
    * Handles API errors with retries and exponential backoff:
      - Rate limits
      - Quota exceeded
      - Invalid key
      - Content moderation
      - Context length
      - Provider availability
      - Request timeouts
    * Returns the results

6.  **Main execution:**
    * Loads configuration from environment variables
    * Parses and applies command-line arguments (overriding env vars)
    * Shows full configuration in verbose mode
    * Lets user select a test file from the 'tests' directory
    * Uses ThreadPoolExecutor for concurrent API requests
    * Writes results to both:
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

1.  **`get_result_files()`:**
    * Lists CSV files from results directory and subdirectories
    * Sorts by modification time
    * Returns list of (file_path, modification_time) tuples

2.  **`select_result_file()`:**
    * Shows last 3 modified files for selection
    * Displays relative paths for better readability
    * Validates user input

3.  **`extract_answer(row, relaxed)`:**
    * Extracts the model's answer from the response string
    * Handles different answer formats
    * Returns 0 if no valid answer found

4.  **Main execution:**
    * Lets user select input file from results directory
    * Creates matching directory structure in data/
    * Example output structure:
      ```
      data/
      ├── Evaluative Thought-Branching Prompt/
      │   └── metrics_gemini-2.0-flash-exp_8.csv
      └── custom/
          └── metrics_gpt-4_8.csv
      ```
    * Processes model responses:
      - Extracts answers
      - Calculates correctness
      - Handles single and multi-size test files
      - Computes lineage scores
    * Outputs results:
      - Saves to data directory with metrics_ prefix
      - Also prints to stdout for piping

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
   - Organized by prompt name (from system prompt file)
   - Custom prompts go in 'results/custom/'
   - Files named as `{model_name}_{size}.csv`
   - Example structure:
     ```
     results/
     ├── Evaluative Thought-Branching Prompt/  # From prompt file
     │   ├── gemini-2.0-flash-exp_8.csv
     │   └── mistral-saba_64.csv
     └── custom/  # For non-file prompts
         ├── gpt-4_8.csv
         └── claude-3_16.csv
     ```
   - Model names are cleaned (e.g., "google/gemini-2.0-flash-exp:free" -> "gemini-2.0-flash-exp")

### Typical Workflow

1. **Generate Tests:**
   ```bash
   ./lineage_bench.py -l 8
   ```
   - Creates file in tests/ directory: `8_20250221_0401.csv`
   - Contains lineage relationship quizzes

2. **Run Model Tests:**
   ```bash
   ./run_openrouter.py -m "google/gemini-2.0-flash-exp:free" -s "prompts/evaluative.md"
   ```
   - Shows last 3 test files for selection
   - Creates prompt-specific directory in results/
   - Saves results as `gemini-2.0-flash-exp_8.csv`
   - Example: `results/Evaluative Thought-Branching Prompt/gemini-2.0-flash-exp_8.csv`

3. **Analyze Results:**
   ```bash
   ./compute_metrics.py
   ```
   - Shows last 3 result files for selection
   - Creates matching directory in data/
   - Saves metrics with prefix: `metrics_gemini-2.0-flash-exp_8.csv`
   - Example: `data/Evaluative Thought-Branching Prompt/metrics_gemini-2.0-flash-exp_8.csv`
   - Also outputs to stdout for piping

4. **Visualize Results:**
   ```bash
   ./compute_metrics.py | ./plot_line.py -o plots/lineage_scores.png
   ```
   - Creates visualizations from metrics
   - Can use either line or stacked plots
   - Saves plots to specified output file
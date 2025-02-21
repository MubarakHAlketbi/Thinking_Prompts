#!/usr/bin/env -S python3 -u

import os
import csv
import sys
import argparse
import time
import json
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pathlib import Path
from typing import List, Tuple, Optional

load_dotenv()

def get_env_defaults() -> dict:
    """Get default values from environment variables."""
    return {
        'model': os.getenv('OPENROUTER_MODEL', 'openrouter/auto'),
        'provider': os.getenv('OPENROUTER_PROVIDER'),
        'effort': os.getenv('OPENROUTER_EFFORT'),
        'threads': int(os.getenv('OPENROUTER_THREADS', '8')),
        'system_prompt': os.getenv('OPENROUTER_SYSTEM_PROMPT'),
        'system_prompt_file': os.getenv('OPENROUTER_SYSTEM_PROMPT_FILE'),
        'referer': os.getenv('OPENROUTER_REFERER'),
        'title': os.getenv('OPENROUTER_TITLE'),
        'fallbacks': os.getenv('OPENROUTER_FALLBACKS', 'true').lower() == 'true',
        'data_privacy': os.getenv('OPENROUTER_DATA_PRIVACY'),
        'require_params': os.getenv('OPENROUTER_REQUIRE_PARAMS', 'false').lower() == 'true',
        'quantization': os.getenv('OPENROUTER_QUANTIZATION'),
        'ignore_providers': os.getenv('OPENROUTER_IGNORE_PROVIDERS'),
        'fallback_models': os.getenv('OPENROUTER_FALLBACK_MODELS')
    }

def parse_model_name(model: str) -> str:
    """Parse model name to remove provider prefix and version suffix."""
    # Remove provider prefix (before /)
    if '/' in model:
        model = model.split('/')[-1]
    # Remove version suffix (after :)
    if ':' in model:
        model = model.split(':')[0]
    return model

def get_prompt_folder_name(prompt_path: Optional[str]) -> str:
    """Get folder name from prompt file path or return 'custom'."""
    if not prompt_path or not os.path.isfile(prompt_path):
        return 'custom'
    
    # Get the file name without extension
    folder_name = os.path.splitext(os.path.basename(prompt_path))[0]
    return folder_name

def extract_size_from_filename(filename: str) -> str:
    """Extract size number from test file name.
    
    Test files are named: {length}_{date}_{time}.csv
    Example: 8_20250221_0401.csv -> returns "8"
    """
    try:
        # Get just the filename without path
        base_name = os.path.basename(filename)
        # Split on underscore and take first part (the length)
        size = base_name.split('_')[0]
        # Verify it's a number
        int(size)  # This will raise ValueError if not a number
        return size
    except (IndexError, ValueError) as e:
        print(f"Error extracting size from filename {filename}: {e}", file=sys.stderr)
        return "unknown"

def get_test_files() -> List[Tuple[Path, float]]:
    """Get list of CSV files from tests directory sorted by modification time."""
    tests_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'tests'
    if not tests_dir.exists():
        print(f"Error: Tests directory not found at {tests_dir}", file=sys.stderr)
        sys.exit(1)
        
    files = [(f, f.stat().st_mtime) for f in tests_dir.glob('*.csv')]
    return sorted(files, key=lambda x: x[1], reverse=True)

def select_test_file() -> Path:
    """Display last 3 test files and let user select one."""
    files = get_test_files()
    if not files:
        print("Error: No CSV files found in tests directory", file=sys.stderr)
        sys.exit(1)
        
    print("\nAvailable test files (last 3):", file=sys.stderr)
    for i, (file, mtime) in enumerate(files[:3], 1):
        print(f"{i}. {file.name} (modified: {time.ctime(mtime)})", file=sys.stderr)
        
    while True:
        try:
            choice = input("\nSelect a file (1-3): ")
            idx = int(choice) - 1
            if 0 <= idx < min(3, len(files)):
                return files[idx][0]
            print("Invalid choice. Please select a number between 1 and 3", file=sys.stderr)
        except ValueError:
            print("Invalid input. Please enter a number", file=sys.stderr)


def get_system_prompt(prompt_arg: str) -> str:
    """
    Get system prompt from various sources:
    1. Direct text input
    2. File path (.txt or .md)
    3. Default prompt if none provided
    """
    DEFAULT_SYSTEM_PROMPT = """You are a master of logical thinking. You carefully analyze the premises step by step, take detailed notes and draw intermediate conclusions based on which you can find the final answer to any question."""
    
    if not prompt_arg:
        return DEFAULT_SYSTEM_PROMPT
        
    # Check if it's a file path
    if isinstance(prompt_arg, str) and os.path.isfile(prompt_arg):
        if prompt_arg.endswith(('.txt', '.md')):
            try:
                with open(prompt_arg, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        return content
                    print(f"Warning: Empty prompt file: {prompt_arg}", file=sys.stderr)
                    return DEFAULT_SYSTEM_PROMPT
            except Exception as e:
                print(f"Warning: Error reading prompt file {prompt_arg}: {e}", file=sys.stderr)
                return DEFAULT_SYSTEM_PROMPT
        else:
            print(f"Warning: Unsupported file type for prompt: {prompt_arg}", file=sys.stderr)
            return DEFAULT_SYSTEM_PROMPT
            
    # If not a file or file reading failed, return the argument itself
    return prompt_arg

# Get defaults from environment
env_defaults = get_env_defaults()

# Set up the argument parser for command-line options.
parser = argparse.ArgumentParser(
    description="Test LLM models using the OpenRouter API. Defaults can be set in .env file."
)
parser.add_argument("-m", "--model",
                   help=f"OpenRouter model name. Default: {env_defaults['model']}",
                   default=env_defaults['model'])
parser.add_argument("-p", "--provider",
                   help="OpenRouter provider name.",
                   default=env_defaults['provider'])
parser.add_argument("-e", "--effort",
                   help="Reasoning effort (o1 model only).",
                   default=env_defaults['effort'])
parser.add_argument("-t", "--threads",
                   help="Number of threads to use.",
                   type=int,
                   default=env_defaults['threads'])
parser.add_argument("-v", "--verbose",
                   help="Enable verbose output.",
                   action="store_true")
parser.add_argument("-s", "--system-prompt",
                   help="System prompt text or file path (.txt/.md). Can also be set via OPENROUTER_SYSTEM_PROMPT or OPENROUTER_SYSTEM_PROMPT_FILE in .env",
                   default=env_defaults['system_prompt'] or env_defaults['system_prompt_file'])
parser.add_argument("--referer",
                   help="Site URL for rankings on openrouter.ai.",
                   default=env_defaults['referer'])
parser.add_argument("--title",
                   help="Site title for rankings on openrouter.ai.",
                   default=env_defaults['title'])
parser.add_argument("-f", "--fallbacks",
                   help="Allow fallbacks to other providers.",
                   type=lambda x: (str(x).lower() == 'true'),
                   default=env_defaults['fallbacks'])
parser.add_argument("--data-privacy",
                   help="Set data collection preference ('allow' or 'deny').",
                   choices=['allow', 'deny'],
                   default=env_defaults['data_privacy'])
parser.add_argument("--require-params",
                   help="Only use providers that support all parameters.",
                   action="store_true",
                   default=env_defaults['require_params'])
parser.add_argument("--quantization",
                   help="Filter providers by quantization level.",
                   choices=['int4', 'int8', 'fp6', 'fp8', 'fp16', 'bf16', 'fp32'],
                   default=env_defaults['quantization'])
parser.add_argument("--ignore-providers",
                   help="Comma-separated list of providers to ignore.",
                   default=env_defaults['ignore_providers'])
parser.add_argument("--fallback-models",
                   help="Comma-separated list of fallback models to try if primary model fails.",
                   default=env_defaults['fallback_models'])

args = parser.parse_args()

# Print configuration if verbose
if args.verbose:
    print("\nConfiguration:", file=sys.stderr)
    for arg, value in vars(args).items():
        if value is not None:
            print(f"{arg}: {value}", file=sys.stderr)
    print("", file=sys.stderr)

# Assign arguments to variables
model_name = args.model if args.model else "openrouter/auto"
provider_name = args.provider  # Keep as string, split when needed
system_prompt = get_system_prompt(args.system_prompt)  # Always get a system prompt (default if none provided)
reasoning_effort = args.effort
num_threads = args.threads
is_verbose = args.verbose
referer = args.referer
site_title = args.title
allow_fallbacks = args.fallbacks
data_privacy = args.data_privacy
require_params = args.require_params
quantization = [args.quantization] if args.quantization else None
ignore_providers = args.ignore_providers.split(',') if args.ignore_providers else None
fallback_models = args.fallback_models.split(',') if args.fallback_models else None

if is_verbose:
    print(f"\nUsing system prompt:\n{system_prompt}\n", file=sys.stderr)

# Get API key from environment
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("Error: OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
    sys.exit(1)

# Let user select test file and prepare CSV reader
test_file = select_test_file()
print(f"\nUsing test file: {test_file}", file=sys.stderr)

# Read all quizzes first to get total count
print("Reading test file...", file=sys.stderr)
with open(test_file, 'r', encoding='utf-8') as f:
    quiz_count = sum(1 for _ in csv.reader(f))
print(f"Found {quiz_count} quizzes to process", file=sys.stderr)

print(f"\nStarting processing with {num_threads} threads...", file=sys.stderr)
quiz_reader = csv.reader(open(test_file, 'r', encoding='utf-8'), delimiter=',', quotechar='"')

def make_request(row):
    # Makes a request to the OpenRouter API with retries and error handling.

    global provider_name
    global system_prompt
    global reasoning_effort
    global api_key
    global is_verbose
    global referer
    global site_title
    global allow_fallbacks
    global data_privacy

    retries = 0
    max_retries = 5
    base_delay = 1
    jitter = 0.25

    time.sleep(1)  # Add a 1-second delay before each request

    if is_verbose:
        print("Processing quiz", file=sys.stderr)

    if len(row) != 4:
        print(f"Error: Invalid input row: {row}. Expected 4 values.", file=sys.stderr)
        return  ["", "", "", "", "", "", "", "", ""] # Return empty values to skip this row

    problem_size, relation_name, correct_answer, quiz = row

    # Construct the messages for the API request.
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": quiz}
    ]

    # Prepare the request data.
    request_data = {
        "model": model_name,
        "temperature": 0.01,
        "seed": 42,
        "messages": messages
    }

    # Add fallback models if specified
    if fallback_models:
        request_data["models"] = [model_name] + fallback_models

    # Add provider options if any are specified
    provider_options = {}
    
    if provider_name:
        # Split provider names into array and remove any empty strings
        provider_options["order"] = [p.strip() for p in provider_name.split(',') if p.strip()]
    if allow_fallbacks is not None:
        provider_options["allow_fallbacks"] = allow_fallbacks
    if data_privacy:
        provider_options["data_collection"] = data_privacy
    if require_params:
        provider_options["require_parameters"] = True
    if quantization:
        provider_options["quantizations"] = quantization
    if ignore_providers:
        provider_options["ignore"] = ignore_providers

    if provider_options:
        request_data["provider"] = provider_options

    if reasoning_effort:
        assert(reasoning_effort in ["low", "medium", "high"])
        request_data["reasoning_effort"] = reasoning_effort

    # Retry loop with exponential backoff.
    while True:
        try:
            # Set up headers for the request.
            headers = { "Authorization": f"Bearer {api_key}" }
            if referer:
                headers["HTTP-Referer"] = referer
            if site_title:
                headers["X-Title"] = site_title

            # Make the API request.
            response = requests.post(
                url = "https://openrouter.ai/api/v1/chat/completions",
                headers = headers,
                data=json.dumps(request_data),
            )

            if is_verbose:
                print(f"Response status code: {response.status_code}", file=sys.stderr)

            if response.status_code != 200:
                print(f"Error response: {response.text}", file=sys.stderr)
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", str(response.text))

                    # Handle different error codes with specific actions.
                    if response.status_code == 429:
                        print("Rate limit exceeded. Implementing exponential backoff.", file=sys.stderr)
                        retries += 1
                        if retries > max_retries:
                            print("Max retries exceeded. Giving up.", file=sys.stderr)
                            return  ["", "", "", "", "", "", "", "", ""]
                        delay = base_delay * (2 ** (retries -1)) * (1 + random.uniform(-jitter, jitter))
                        print(f"Waiting {delay:.2f} seconds before retrying.", file=sys.stderr)
                        time.sleep(delay)
                        continue
                    elif response.status_code == 402:
                        print("API quota exceeded. Please check your OpenRouter account.", file=sys.stderr)
                        return  ["", "", "", "", "", "", "", "", ""]
                    elif response.status_code == 401:
                        print("Invalid API key. Please check your OpenRouter API key.", file=sys.stderr)
                        return  ["", "", "", "", "", "", "", "", ""]
                    elif response.status_code == 400:
                        if "moderation" in error_msg.lower():
                            print("Content was flagged by moderation. Please revise your input.", file=sys.stderr)
                            return  ["", "", "", "", "", "", "", "", ""]
                        elif "context_length" in error_msg.lower():
                            print("Input exceeds model's context length. Please reduce the input size.", file=sys.stderr)
                            return  ["", "", "", "", "", "", "", "", ""]
                    elif response.status_code == 502:
                        print("Provider service is currently unavailable. Waiting 60 seconds before retrying.", file=sys.stderr)
                        time.sleep(60)
                        continue
                    elif response.status_code == 504:
                        print("Request timed out. The model may be overloaded. Waiting 60 seconds before retrying.", file=sys.stderr)
                        time.sleep(60)
                        continue
                    else:
                        print(f"Unhandled error: {error_msg}", file=sys.stderr)
                        return  ["", "", "", "", "", "", "", "", ""]
                except:
                    print(f"Error decoding JSON response: {response.text}", file=sys.stderr)
                    return ["", "", "", "", "", "", "", "", ""]

            # Extract the model's response from the JSON response.
            response_json = response.json()
            model_response = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            provider_name = response_json.get("provider", "") # use get here as well
            break

        except requests.RequestException as ex:
            print(f"Request exception: {ex}. Implementing exponential backoff.", file=sys.stderr)
            retries += 1
            if retries > max_retries:
                print("Max retries exceeded. Giving up.", file=sys.stderr)
                return  ["", "", "", "", "", "", "", "", ""]
            delay = base_delay * (2 ** (retries -1)) * (1 + random.uniform(-jitter, jitter))
            print(f"Waiting {delay:.2f} seconds before retrying.", file=sys.stderr)
            time.sleep(delay)
            continue

        except Exception as ex:
            print(f"Caught exception: {ex}", file=sys.stderr)
            return  ["", "", "", "", "", "", "", "", ""]

    # Return the results.
    return [problem_size, relation_name, correct_answer, quiz, model_name, provider_name, reasoning_effort, system_prompt, model_response]

# Get base results directory and create prompt-specific subdirectory
base_results_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'results'
prompt_dir = get_prompt_folder_name(args.system_prompt)
results_dir = base_results_dir / prompt_dir
os.makedirs(results_dir, exist_ok=True)

# Parse model name and get size from test file
clean_model_name = parse_model_name(model_name)
size = extract_size_from_filename(test_file)  # Pass full Path object

# Create output file name: {model_name}_{size}.csv
output_file = results_dir / f"{clean_model_name}_{size}.csv"

if is_verbose:
    print(f"\nModel name: {clean_model_name}", file=sys.stderr)
    print(f"Test size: {size}", file=sys.stderr)

if is_verbose:
    print(f"\nResults will be saved to: {output_file}", file=sys.stderr)

# Use a ThreadPoolExecutor to process quizzes concurrently.
print("Initializing threads...", file=sys.stderr)
with ThreadPoolExecutor(max_workers=num_threads) as executor:
    # Submit all tasks and get futures
    futures = list(map(lambda x: executor.submit(make_request, x), quiz_reader))
    
    # Wait for first thread to start processing
    while not any(f.running() for f in futures):
        time.sleep(0.1)
    print(f"Threads active and processing...", file=sys.stderr)
    
    # Get results as they complete
    results = [f.result() for f in futures]

# Write results to file
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    file_writer = csv.writer(f)
    processed = 0
    for result in results:
        file_writer.writerow(result)
        processed += 1
        progress = (processed / quiz_count) * 100
        print(f"Progress: {processed}/{quiz_count} quizzes ({progress:.1f}%)", file=sys.stderr, end='\r')
    
    print("", file=sys.stderr)  # Clear the progress line
    print(f"\nCompleted processing {processed} quizzes", file=sys.stderr)
    print(f"Results saved to: {output_file}", file=sys.stderr)

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
from typing import List, Tuple

load_dotenv()

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


def get_system_prompt(prompt_arg):
    # Reads system prompt from a file or returns the argument itself
    if os.path.isfile(prompt_arg) and (prompt_arg.endswith(".txt") or prompt_arg.endswith(".md")):
        with open(prompt_arg, 'r') as f:
            return f.read()
    return prompt_arg

DEFAULT_SYSTEM_PROMPT="You are a master of logical thinking. You carefully analyze the premises step by step, take detailed notes and draw intermediate conclusions based on which you can find the final answer to any question."

# Set up the argument parser for command-line options.
parser = argparse.ArgumentParser()
parser.add_argument("-m", "--model", help="OpenRouter model name.", required=True)
parser.add_argument("-p", "--provider", help="OpenRouter provider name.")
parser.add_argument("-e", "--effort", help="Reasoning effort (o1 model only).")
parser.add_argument("-t", "--threads", help="Number of threads to use.", type=int, default=8)
parser.add_argument("-v", "--verbose", help="Enable verbose output.", action="store_true")
parser.add_argument("-s", "--system-prompt", help="Use given system prompt. By default, the system prompt is not used. When this option is passed without a value, the default system prompt value is used: " + repr(DEFAULT_SYSTEM_PROMPT), const=DEFAULT_SYSTEM_PROMPT, default=None, nargs='?')
parser.add_argument("--referer", help="Site URL for rankings on openrouter.ai.")
parser.add_argument("--title", help="Site title for rankings on openrouter.ai.")
parser.add_argument("-f", "--fallbacks", help="Allow fallbacks to other providers. Defaults to True.", type=lambda x: (str(x).lower() == 'true'), default=True)
parser.add_argument("--data-privacy", help="Set data collection preference ('allow' or 'deny').", choices=['allow', 'deny'])
parser.add_argument("--require-params", help="Only use providers that support all parameters.", action="store_true")
parser.add_argument("--quantization", help="Filter providers by quantization level.", choices=['int4', 'int8', 'fp6', 'fp8', 'fp16', 'bf16', 'fp32'])
parser.add_argument("--ignore-providers", help="Comma-separated list of providers to ignore.")
parser.add_argument("--fallback-models", help="Comma-separated list of fallback models to try if primary model fails.")

args = parser.parse_args()

# Assign arguments to variables
model_name = args.model if args.model else "openrouter/auto"
provider_name = args.provider.split(',') if args.provider else None
system_prompt = get_system_prompt(args.system_prompt) if args.system_prompt else args.system_prompt
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

# Get API key from environment
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("Error: OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
    sys.exit(1)

# Let user select test file and prepare CSV reader/writer
test_file = select_test_file()
print(f"\nUsing test file: {test_file}", file=sys.stderr)

quiz_reader = csv.reader(open(test_file, 'r', encoding='utf-8'), delimiter=',', quotechar='"')
csv_writer = csv.writer(sys.stdout)


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
    system_messages=[{"role": "system", "content": system_prompt }]
    messages=[{"role": "user", "content": quiz }]
    if system_prompt is not None:
        messages = system_messages + messages

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
        provider_options["order"] = provider_name
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

# Create results directory if it doesn't exist
results_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'results'
os.makedirs(results_dir, exist_ok=True)

# Prepare output file with same name as input file
output_file = results_dir / test_file.name

# Use a ThreadPoolExecutor to process quizzes concurrently.
with ThreadPoolExecutor(max_workers=num_threads) as executor:
    results = executor.map(make_request, quiz_reader)

# Write results to both stdout and results file
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    file_writer = csv.writer(f)
    # Convert results iterator to list to avoid consuming it
    results_list = list(results)
    # Write results to both writers
    for result in results_list:
        csv_writer.writerow(result)  # Write to stdout
        file_writer.writerow(result) # Write to file
    print(f"\nResults saved to: {output_file}", file=sys.stderr)

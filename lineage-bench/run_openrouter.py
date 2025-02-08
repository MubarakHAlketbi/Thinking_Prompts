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

load_dotenv()
from dotenv import load_dotenv

load_dotenv()


def get_system_prompt(prompt_arg):
    if os.path.isfile(prompt_arg) and (prompt_arg.endswith(".txt") or prompt_arg.endswith(".md")):
        with open(prompt_arg, 'r') as f:
            return f.read()
    return prompt_arg

DEFAULT_SYSTEM_PROMPT="You are a master of logical thinking. You carefully analyze the premises step by step, take detailed notes and draw intermediate conclusions based on which you can find the final answer to any question."

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

args = parser.parse_args()
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

quiz_reader = csv.reader(sys.stdin, delimiter=',', quotechar='"')
csv_writer = csv.writer(sys.stdout)
api_key = os.getenv("OPENROUTER_API_KEY")


def make_request(row):
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

    if is_verbose:
        print("Processing quiz", file=sys.stderr)

    problem_size, relation_name, correct_answer, quiz = row

    system_messages=[{"role": "system", "content": system_prompt }]
    messages=[{"role": "user", "content": quiz }]
    if system_prompt is not None:
        messages = system_messages + messages

    request_data = {
        "model": model_name,
        "temperature": 0.01,
        "seed": 42,
        "messages": messages
    }

    if provider_name or allow_fallbacks is not None or data_privacy:
        request_data["provider"] = {}
        if provider_name:
            request_data["provider"]["order"] = provider_name
        if allow_fallbacks is not None:
            request_data["provider"]["allow_fallbacks"] = allow_fallbacks
        if data_privacy:
            request_data["provider"]["data_collection"] = data_privacy

    if reasoning_effort:
        assert(reasoning_effort in ["low", "medium", "high"])
        request_data["reasoning_effort"] = reasoning_effort

    while True:
        try:
            headers = { "Authorization": f"Bearer {api_key}" }
            if referer:
                headers["HTTP-Referer"] = referer
            if site_title:
                headers["X-Title"] = site_title
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

    return [problem_size, relation_name, correct_answer, quiz, model_name, provider_name, reasoning_effort, system_prompt, model_response]

with ThreadPoolExecutor(max_workers=num_threads) as executor:
    results = executor.map(make_request, quiz_reader)

for result in results:
    csv_writer.writerow(result)


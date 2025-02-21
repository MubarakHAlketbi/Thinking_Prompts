#!/usr/bin/env python3

import codecs
import random
import sys
import csv
import os
import time
import requests
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, Tuple

# Default prompt template for the quiz.
DEFAULT_PROMPT = """Given the following lineage relationships:
{quiz_relations}
{quiz_question}
Select the correct answer:
{quiz_answers}
Enclose the selected answer number in the <ANSWER> tag, for example: <ANSWER>1</ANSWER>."""

# List of male names for generating quizzes.
male_names = [
    'James', 'Robert', 'John', 'Michael', 'David',
    'William', 'Richard', 'Joseph', 'Thomas', 'Christopher',
    'Charles', 'Daniel', 'Matthew', 'Anthony', 'Mark',
    'Donald', 'Steven', 'Andrew', 'Paul', 'Joshua',
    'Kenneth', 'Kevin', 'Brian', 'George', 'Timothy',
    'Ronald', 'Jason', 'Edward', 'Jeffrey', 'Ryan',
    'Jacob', 'Gary', 'Nicholas', 'Eric', 'Jonathan',
    'Stephen', 'Larry', 'Justin', 'Scott', 'Brandon',
    'Benjamin', 'Samuel', 'Gregory', 'Alexander', 'Patrick',
    'Frank', 'Raymond', 'Jack', 'Dennis', 'Jerry',
    'Tyler', 'Aaron', 'Jose', 'Adam', 'Nathan',
    'Henry', 'Zachary', 'Douglas', 'Peter', 'Kyle',
    'Noah', 'Ethan', 'Jeremy', 'Walter', 'Christian',
    'Keith', 'Roger', 'Terry', 'Austin', 'Sean',
    'Gerald', 'Carl', 'Harold', 'Dylan', 'Arthur',
    'Lawrence', 'Jordan', 'Jesse', 'Bryan', 'Billy',
    'Bruce', 'Gabriel', 'Joe', 'Logan', 'Alan',
    'Juan', 'Albert', 'Willie', 'Elijah', 'Wayne',
    'Randy', 'Vincent', 'Mason', 'Roy', 'Ralph',
    'Bobby', 'Russell', 'Bradley', 'Philip', 'Eugene'
]

# List of female names for generating quizzes.
female_names = [
    'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth',
    'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen',
    'Lisa', 'Nancy', 'Betty', 'Sandra', 'Margaret',
    'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle',
    'Carol', 'Amanda', 'Melissa', 'Deborah', 'Stephanie',
    'Dorothy', 'Rebecca', 'Sharon', 'Laura', 'Cynthia',
    'Amy', 'Kathleen', 'Angela', 'Shirley', 'Brenda',
    'Emma', 'Anna', 'Pamela', 'Nicole', 'Samantha',
    'Katherine', 'Christine', 'Helen', 'Debra', 'Rachel',
    'Carolyn', 'Janet', 'Maria', 'Catherine', 'Heather',
    'Diane', 'Olivia', 'Julie', 'Joyce', 'Victoria',
    'Ruth', 'Virginia', 'Lauren', 'Kelly', 'Christina',
    'Joan', 'Evelyn', 'Judith', 'Andrea', 'Hannah',
    'Megan', 'Cheryl', 'Jacqueline', 'Martha', 'Madison',
    'Teresa', 'Gloria', 'Sara', 'Janice', 'Ann',
    'Kathryn', 'Abigail', 'Sophia', 'Frances', 'Jean',
    'Alice', 'Judy', 'Isabella', 'Julia', 'Grace',
    'Amber', 'Denise', 'Danielle', 'Marilyn', 'Beverly',
    'Charlotte', 'Natalie', 'Theresa', 'Diana', 'Brittany',
    'Doris', 'Kayla', 'Alexis', 'Lori', 'Marie'
]

# Enumeration for different types of quiz questions.
class QuizType(Enum):
    ANCESTOR = 1
    DESCENDANT = 2
    COMMON_ANCESTOR = 3
    COMMON_DESCENDANT = 4
    OTHER = 5

# Templates for the answer options in the quiz.
answer_templates = [
    (QuizType.ANCESTOR, "{p1_name} is {p2_name}'s ancestor."),
    (QuizType.DESCENDANT, "{p1_name} is {p2_name}'s descendant."),
    (QuizType.COMMON_ANCESTOR, "{p1_name} and {p2_name} share a common ancestor."),
    (QuizType.COMMON_DESCENDANT, "{p1_name} and {p2_name} share a common descendant."),
    (QuizType.OTHER, "None of the above is correct."),
]

def generate_quiz(length, quiz_type, shuffle=False, prompt=DEFAULT_PROMPT):
    # Generates a single quiz of the specified type and length.

    # Randomly select names for the quiz.
    character_names = random.sample(male_names + female_names, length)

    # Generate the lineage relationships based on the quiz type.
    match quiz_type:
        case QuizType.ANCESTOR:
            ancestor_relations = [(i, i + 1) for i in range(length - 1)]
        case QuizType.DESCENDANT:
            ancestor_relations = [(i + 1, i) for i in range(length - 1)]
        case QuizType.COMMON_ANCESTOR:
            common_pos = random.randint(1, length - 2)
            ancestor_relations = [(i + 1, i) if i + 1 <= common_pos else (i, i + 1) for i in range(length - 1)]
        case QuizType.COMMON_DESCENDANT:
            common_pos = random.randint(1, length - 2)
            ancestor_relations = [(i, i + 1) if i + 1 <= common_pos else (i + 1, i) for i in range(length - 1)]
        case _:
            raise ValueError("Unsupported quiz type")
    
    # Shuffle the relationships if specified.
    if shuffle:
        random.shuffle(ancestor_relations)

    # Build the string describing the lineage relationships.
    quiz_relations_str = ""
    for p1, p2 in ancestor_relations:
        p1_name = character_names[p1]
        p2_name = character_names[p2]

        if random.choice([True, False]):
            quiz_relations_str += f"* {p1_name} is {p2_name}'s ancestor.\n"
        else:
            quiz_relations_str += f"* {p2_name} is {p1_name}'s descendant.\n"

    # Define the quiz question and get the names of the two people in question.
    p1_name = character_names[0]
    p2_name = character_names[length-1]
    quiz_question_str = f"Determine the lineage relationship between {p1_name} and {p2_name}."
 
    # Build the answer options string.
    answer_options = answer_templates[:-1]
    if shuffle:
        random.shuffle(answer_options)
    answer_options.append(answer_templates[-1])

    quiz_answers_str = ""
    correct_answer_num = 0
    for i, (quiz_answer_type, quiz_answer_template) in enumerate(answer_options):
        answer_num = i + 1
        quiz_answer = quiz_answer_template.format(p1_name=p1_name, p2_name=p2_name);
        quiz_answers_str += f"{answer_num}. {quiz_answer}\n"
        if quiz_answer_type == quiz_type:
            correct_answer_num = answer_num

    assert(correct_answer_num != 0)

    # Format the complete quiz using the provided prompt template.
    quiz = prompt.format(quiz_relations=quiz_relations_str.strip(), quiz_question=quiz_question_str.strip(), quiz_answers=quiz_answers_str.strip())
    return quiz, correct_answer_num

def generate_quizzes(length, num_quizzes=10, prompt=DEFAULT_PROMPT, shuffle=False, seed=None):
    # Generates multiple quizzes of different types.
    if seed is not None:
        random.seed(seed)
    quiz_types = list(QuizType)
    # do not generate QuizType.OTHER quizes
    quiz_types.pop()
    for quiz_type in quiz_types:
        for i in range(num_quizzes):
            quiz, correct_answer = generate_quiz(length, quiz_type, shuffle=shuffle, prompt=prompt)
            if quiz is not None and correct_answer is not None:  # Explicit None check
                yield (str(quiz_type).removeprefix("QuizType."), correct_answer, quiz)

def try_get_time_from_source(url: str, max_retries: int = 3) -> Optional[datetime]:
    """Try to get time from a specific source with retries."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                if 'worldtimeapi.org' in url:
                    time_data = response.json()
                    return datetime.fromisoformat(time_data['datetime'].replace('Z', '+00:00'))
                elif 'timeapi.io' in url:
                    time_data = response.json()
                    return datetime.fromisoformat(time_data['dateTime'])
                elif 'timeapi.org' in url:
                    return datetime.fromisoformat(response.text.strip())
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed for {url}: {e}", file=sys.stderr)
                time.sleep(1)
    return None

def get_online_time() -> datetime:
    """Get current time from multiple online time servers with fallback."""
    time_sources = [
        'http://worldtimeapi.org/api/timezone/UTC',
        'https://timeapi.io/api/Time/current/zone?timeZone=UTC',
        'https://timeapi.org/utc/now'
    ]
    
    for source in time_sources:
        dt = try_get_time_from_source(source)
        if dt:
            return dt
        print(f"Warning: Could not get time from {source}", file=sys.stderr)
    
    print("Warning: All online time sources failed, using local time", file=sys.stderr)
    return datetime.now(UTC)

# Main execution block when the script is run directly.
if __name__ == '__main__':
    import argparse
    # Set up the argument parser for command-line options.
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--length", help = "Number of people connected with lineage relationships in the quiz.", type=int, required=True)
    parser.add_argument("-p", "--prompt", help = "Prompt template of the quiz. The default prompt template is: " + repr(DEFAULT_PROMPT), default=DEFAULT_PROMPT)
    parser.add_argument("-s", "--shuffle", help = "Shuffle the order of lineage relations in the quiz.", action="store_true")
    parser.add_argument("-n", "--number", help = "Number of quizzes generated for each valid answer option.", default=10, type=int)
    parser.add_argument("-r", "--seed", help = "Random seed value", default=None, type=int)
    args = parser.parse_args()

    # Decode the prompt template to handle escaped characters.
    prompt = codecs.escape_decode(bytes(args.prompt, "utf-8"))[0].decode("utf-8")

    # Create tests directory if it doesn't exist
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    os.makedirs(tests_dir, exist_ok=True)

    # Get timestamp from online source
    current_time = get_online_time()
    timestamp = current_time.strftime('%Y%m%d_%H%M')
    output_file = os.path.join(tests_dir, f'{args.length}_{timestamp}.csv')

    # Create a CSV writer to output the generated quizzes
    with open(output_file, 'w', newline='') as f:
        csv_writer = csv.writer(f)
        try:
            for relation_name, correct_answer, quiz in generate_quizzes(args.length, args.number, prompt, args.shuffle, args.seed):
                csv_writer.writerow([args.length, relation_name, correct_answer, quiz])
            print(f"Output saved to: {output_file}", file=sys.stderr)
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)

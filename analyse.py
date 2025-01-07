import openai
import os
from openai import OpenAI

import logging

logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def is_binary_file(filepath):
    """Check if a file is binary."""
    try:
        with open(filepath, 'rb') as file:
            chunk = file.read(1024)
            if b'\0' in chunk:
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking if file is binary: {e}")
        return True


def analyze_dockerfile(filepath):
    """Analyze the Dockerfile and group commands."""
    commands = []
    files_to_analyze = []
    current_command = None

    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            # Skip comments or empty lines
            if not line or line.startswith('#'):
                continue

            # Check if the line starts a new Dockerfile instruction
            if any(line.startswith(instruction) for instruction in ("FROM", "ENV", "RUN", "COPY", "CMD", "ENTRYPOINT", "ADD")):
                if current_command:  # Save the previous command
                    commands.append(current_command)
                current_command = line  # Start a new command

                # Extract file paths from COPY commands
                if line.startswith("COPY"):
                    parts = line.split()
                    if len(parts) > 1:
                        # Assuming the format: COPY <source> <destination>
                        source_files = parts[1:-1]  # All but the last element
                        files_to_analyze.extend(source_files)
            else:
                if current_command:  # Append to the current command
                    current_command += f" \\\n{line}"

        if current_command:  # Add the last command
            commands.append(current_command)

    return commands, files_to_analyze


def analyze_file_content(filepath):
    """Analyze the content of a given file."""
    logging.info(f"Analyzing file: {filepath}")
    with open(filepath, 'r') as file:
        content = file.read()

    prompt = f"Explain the purpose of the following file content:\n\n{content}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
        {
        "role": "user",
        "content": prompt
        },
    ],
    response_format={
        "type": "text"
    },
    temperature=1,
    max_completion_tokens=1000,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )

    explanation = response.choices[0].message.content
    return explanation


def get_command_details(command):
    """Get details about a Dockerfile command."""
    logging.info(f"Sending API request for command: {command}")
    prompt = f"Explain the following Dockerfile command in detail:\n\n{command}"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
        {
        "role": "user",
        "content": prompt
        },
    ],
    response_format={
        "type": "text"
    },
    temperature=1,
    max_completion_tokens=1000,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )

    explanation = response.choices[0].message.content
    return explanation


def create_readme(commands, file_explanations):
    """Create a README with command and file explanations."""
    table = "| Command | Explanation |\n|---------|-------------|\n"

    for command in commands:
        logging.info(f"Processing command: {command.splitlines()[0]}")
        command_details = get_command_details(command)
        table += f"| `{command}` | {command_details} |\n"

    table += "\n\n## File Content Analysis\n\n"
    for filepath, explanation in file_explanations.items():
        table += f"### {filepath}\n\n{explanation}\n\n"

    with open('README.md', 'w') as readme:
        readme.write("# Dockerfile Command Analysis\n\n")
        readme.write(table)


def main():
    dockerfile_path = '<dockerfile location path>'
    base_dir = os.path.dirname(dockerfile_path)
    commands, files_to_analyze = analyze_dockerfile(dockerfile_path)

    # Analyze the content of the copied files
    file_explanations = {}
    for file_name in files_to_analyze:
        file_path = os.path.join(base_dir, file_name)
        if os.path.exists(file_path) and not is_binary_file(file_path):
            file_explanations[file_name] = analyze_file_content(file_path)
        else:
            logging.info(f"Skipping binary or missing file: {file_name}")

    create_readme(commands, file_explanations)


if __name__ == "__main__":
    main()

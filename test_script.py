import sys

def check_task_description():
    with open('src/agents/openai_dev_task_manager.py', 'r') as f:
        lines = f.readlines()
        print("Lines 10-16 in file:")
        for i, line in enumerate(lines[9:16]):
            print(f"{i+10}: {line.strip()}")

if __name__ == "__main__":
    check_task_description()

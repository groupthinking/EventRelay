import re
import sys

def main():
    try:
        with open('apps/web/vitest_output.txt', 'r') as f:
            content = f.read()
            match = re.search(r'Failed to start forks worker(.*?)Caused by:.*?(\n.*?)+', content, re.DOTALL)
            if match:
                print(match.group(0))
            else:
                # Fallback, just look for the error summary
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if "Error: " in line and "vitest" in line.lower():
                        start = max(0, i - 2)
                        end = min(len(lines), i + 15)
                        print('\n'.join(lines[start:end]))
                        break
                else:
                    print("Could not find the error block.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == '__main__':
    main()

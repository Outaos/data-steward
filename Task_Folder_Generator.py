import os

# Base path for 2025 tasks
BASE_PATH = r"\\spatialfiles2\work\FOR\RSI\SA\Tasks\2025"

# Ask user for task number
task_number = input("Enter Task Number: ").strip()

# Build the full folder path
task_path = os.path.join(BASE_PATH, task_number)

# Subfolders to create
subfolders = [
    "Deliverables",
    "Incoming",
    "Working"
]

try:
    # Create main task folder
    os.makedirs(task_path, exist_ok=True)
    print(f"Created or verified: {task_path}")

    # Create subfolders
    for folder in subfolders:
        sub_path = os.path.join(task_path, folder)
        os.makedirs(sub_path, exist_ok=True)
        print(f"   - {sub_path}")

    print("\nAll folders created successfully!")

except Exception as e:
    print(f"Error: {e}")

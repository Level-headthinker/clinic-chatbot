import json
import os

# Files and folders to skip
SKIP_DIRS = {
    'node_modules', '__pycache__', '.git', 'venv',
    '.venv', 'build', 'dist', '.next', 'coverage',
    'migrations', '.mypy_cache', 'htmlcov'
}

SKIP_FILES = {
    '.env', '.env.local', '.DS_Store', 'package-lock.json',
    'yarn.lock', '.gitignore', 'Thumbs.db', 'project_snapshot.json'
}

# Only include these file types
INCLUDE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.json',
    '.md', '.txt', '.toml', '.yaml', '.yml', '.html',
    '.css', '.sql', '.sh', '.env.example'
}

# Max file size to include (50KB)
MAX_FILE_SIZE = 50 * 1024


def read_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"[Could not read file: {e}]"


def scan_project(root_path):
    project = {
        "project_name": os.path.basename(root_path),
        "root_path": root_path,
        "structure": [],
        "files": {},
        "summary": {
            "total_files": 0,
            "total_lines": 0,
            "file_types": {}
        }
    }

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Remove skipped directories
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith('.')
        ]

        for filename in filenames:
            if filename in SKIP_FILES:
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext not in INCLUDE_EXTENSIONS:
                continue

            filepath = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(filepath, root_path)

            # Skip large files
            try:
                file_size = os.path.getsize(filepath)
                if file_size > MAX_FILE_SIZE:
                    project["files"][relative_path] = {
                        "content": f"[File too large: {file_size} bytes]",
                        "lines": 0,
                        "size": file_size,
                        "extension": ext
                    }
                    continue
            except Exception:
                continue

            content = read_file(filepath)
            lines = len(content.splitlines())

            project["files"][relative_path] = {
                "content": content,
                "lines": lines,
                "size": file_size,
                "extension": ext
            }

            # Update summary
            project["summary"]["total_files"] += 1
            project["summary"]["total_lines"] += lines
            project["summary"]["file_types"][ext] = \
                project["summary"]["file_types"].get(ext, 0) + 1

            # Add to structure list
            project["structure"].append(relative_path)

    return project


def main():
    # Run from R:\clinic-chatbot folder
    root_path = os.getcwd()
    print(f"Scanning: {root_path}")

    project_data = scan_project(root_path)

    output_file = "project_snapshot.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)

    print("\nDone!")
    print(f"   Files scanned:  {project_data['summary']['total_files']}")
    print(f"   Total lines:    {project_data['summary']['total_lines']}")
    print(f"   Output file:    {output_file}")
    print(f"\nFile types found:")
    for ext, count in sorted(project_data['summary']['file_types'].items()):
        print(f"   {ext:15} {count} files")


if __name__ == "__main__":
    main()

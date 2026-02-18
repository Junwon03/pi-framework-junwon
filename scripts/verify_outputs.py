import hashlib
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(BASE, "golden")
TARGET_DIRS = ["output", "data"]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_files(root):
    files = []
    for dirname in TARGET_DIRS:
        base_dir = os.path.join(root, dirname)
        if not os.path.exists(base_dir):
            continue
        for current_root, _, names in os.walk(base_dir):
            for name in names:
                rel = os.path.relpath(os.path.join(current_root, name), root)
                files.append(rel)
    return sorted(files)


def main():
    if not os.path.exists(GOLDEN):
        print("ERROR: golden/ directory does not exist.")
        sys.exit(1)

    expected = list_files(GOLDEN)
    if not expected:
        print("ERROR: golden/output or golden/data is empty.")
        sys.exit(1)

    failed = False
    for rel in expected:
        golden_path = os.path.join(GOLDEN, rel)
        actual_path = os.path.join(BASE, rel)

        if not os.path.exists(actual_path):
            print(f"MISSING: {rel}")
            failed = True
            continue

        golden_hash = sha256(golden_path)
        actual_hash = sha256(actual_path)
        if golden_hash != actual_hash:
            print(f"DIFF: {rel}")
            failed = True

    if failed:
        print("FAIL: output differs from golden baseline.")
        sys.exit(1)

    print("OK: all outputs match golden baseline.")


if __name__ == "__main__":
    main()

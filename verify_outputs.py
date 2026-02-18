import hashlib
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(BASE, "golden")
TARGET_DIRS = ["output", "data"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def should_compare(rel_path):
    # figures는 환경/메타데이터 차이로 해시가 자주 바뀌므로 제외
    if rel_path.startswith("output/figures/"):
        return False

    ext = os.path.splitext(rel_path)[1].lower()

    # output은 csv/txt만 비교, data는 csv만 비교
    if rel_path.startswith("output/"):
        return ext in {".csv", ".txt"}
    if rel_path.startswith("data/"):
        return ext == ".csv"

    return False


def list_files(root):
    files = []
    for d in TARGET_DIRS:
        base_dir = os.path.join(root, d)
        if not os.path.exists(base_dir):
            continue
        for cur, _, names in os.walk(base_dir):
            for name in names:
                rel = os.path.relpath(os.path.join(cur, name), root).replace("\\", "/")
                if should_compare(rel):
                    files.append(rel)
    return sorted(files)


def main():
    if not os.path.exists(GOLDEN):
        print("ERROR: golden/ directory does not exist.")
        sys.exit(1)

    expected = list_files(GOLDEN)
    if not expected:
        print("ERROR: no comparable files in golden.")
        sys.exit(1)

    failed = False
    for rel in expected:
        g = os.path.join(GOLDEN, rel)
        a = os.path.join(BASE, rel)

        if not os.path.exists(a):
            print(f"MISSING: {rel}")
            failed = True
            continue

        if sha256(g) != sha256(a):
            print(f"DIFF: {rel}")
            failed = True

    if failed:
        print("FAIL: output differs from golden baseline.")
        sys.exit(1)

    print("OK: all comparable outputs match golden baseline.")


if __name__ == "__main__":
    main()

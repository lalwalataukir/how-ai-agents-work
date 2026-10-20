"""Build each project's starter from its finished code, and check the result.

    python projects/build.py           # rebuild the starter zips
    python projects/build.py --check   # fail if a zip is out of date

The finished code marks what the learner writes in each milestone:

    # BEGIN m2
    ...the finished code...
    # END m2
    #> ...what the starter has instead...

The starter gets the #> lines, or `raise NotImplementedError` when there are none.
render(text, stage) gives the code as it is after `stage` milestones: 0 is the starter,
and the last milestone is the finished code. The tests use it to check that every stage
passes exactly the milestones it should.
"""
import ast
import io
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
PROJECTS = {  # folder here -> (folder name in the zip, number of milestones)
    "p1-code-review": ("code-reviewer", 5),
    "p2-data-agent": ("data-agent", 6),
    "p3-code-qa": ("code-qa", 6),
    "p4-research-team": ("research-team", 6),
}
SKIP = {".venv", "__pycache__", ".pytest_cache", "review.md", ".env", "shop.db", "charts", "index", "reports"}
BEGIN = re.compile(r"^(\s*)# BEGIN m(\d+)\s*$")
END = re.compile(r"^\s*# END m(\d+)\s*$")
STARTER = re.compile(r"^(\s*)#>(?: (.*)|$)")


def blocks(text):
    """Yield (start, end, milestone, indent, finished lines, starter lines) for each marked block,
    where text.splitlines()[start:end] is the whole block, markers and #> lines included."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        begin = BEGIN.match(lines[i])
        if not begin:
            i += 1
            continue
        indent, number = begin[1], int(begin[2])
        j = i + 1
        while not END.match(lines[j]):
            j += 1
        assert int(END.match(lines[j])[1]) == number, f"BEGIN m{number} closed by {lines[j]!r}"
        k = j + 1
        starter = []
        while k < len(lines) and STARTER.match(lines[k]):
            match = STARTER.match(lines[k])
            starter.append(match[1] + (match[2] or "") if match[2] else "")
            k += 1
        yield i, k, number, indent, lines[i + 1:j], starter or [f'{indent}raise NotImplementedError("milestone {number}")']
        i = k


def render(text, stage):
    """The code after `stage` milestones: finished blocks up to stage, starter blocks after it."""
    lines, out, last = text.splitlines(), [], 0
    for start, end, number, _, finished, starter in blocks(text):
        out += lines[last:start] + (finished if number <= stage else starter)
        last = end
    out += lines[last:]
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def name_of(node):
    """A top-level function's or class's name, or the variable a top-level assignment sets."""
    return getattr(node, "name", None) or getattr(getattr(node, "targets", [None])[0], "id", None)


def milestone_code(text, number):
    """The finished top-level functions, classes and settings that milestone `number` writes, as source."""
    names = []
    tree = ast.parse(text)
    for start, _, n, _, _, _ in blocks(text):
        if n == number:  # the block's first finished line, just after "# BEGIN"
            node = next(node for node in tree.body if node.lineno <= start + 2 <= node.end_lineno)
            if name_of(node) not in names:
                names.append(name_of(node))
    done = render(text, number)
    nodes = {name_of(node): node for node in ast.parse(done).body if name_of(node)}
    return [ast.get_source_segment(done, nodes[name]) for name in names]


def project_files(folder):
    """(path inside the project, text or bytes) for every file the learner gets, at stage 0."""
    root = HERE / folder
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir() or SKIP & set(rel.parts):
            continue
        if rel.as_posix() == "check.py":
            yield rel.as_posix(), (HERE / "check.py").read_bytes()  # one checker for every project
        elif path.suffix == ".py":
            yield rel.as_posix(), render(path.read_text(encoding="utf-8"), 0).encode("utf-8")
        else:
            yield rel.as_posix(), path.read_bytes()


def snapshot(folder, stage, dest):
    """Write the project as it is after `stage` milestones into dest."""
    root = HERE / folder
    for rel, data in project_files(folder):
        target = Path(dest) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".py") and rel != "check.py":
            data = render((root / rel).read_text(encoding="utf-8"), stage).encode("utf-8")
        target.write_bytes(data)


def starter_zip(folder):
    """The starter as zip bytes, the same every time for the same files."""
    name = PROJECTS[folder][0]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel, data in project_files(folder):
            info = zipfile.ZipInfo(f"{name}/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def zip_path(folder):
    return HERE / f"{folder}-starter.zip"


def main(args):
    stale = []
    for folder in PROJECTS:
        assert (HERE / folder / "check.py").read_bytes() == (HERE / "check.py").read_bytes(), \
            f"{folder}/check.py differs from projects/check.py: copy it over"
        data = starter_zip(folder)
        if zip_path(folder).is_file() and zip_path(folder).read_bytes() == data:
            continue
        if "--check" in args:
            stale.append(zip_path(folder).name)
        else:
            zip_path(folder).write_bytes(data)
            print("wrote", zip_path(folder).name, len(data), "bytes")
    if stale:
        sys.exit("Out of date, run python projects/build.py: " + ", ".join(stale))


if __name__ == "__main__":
    main(sys.argv[1:])

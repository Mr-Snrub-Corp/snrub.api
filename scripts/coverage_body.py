"""Report coverage split by import-time vs function-body lines.

`coverage report` weights every measured statement equally, but over half the
statements in `app/` are imports, decorators, SQLModel field declarations and
function signatures. Those execute the moment the test suite imports the app,
so they sit near 100% whether or not a test exists, and they pull the headline
number up with them.

This splits the same `.coverage` data into two buckets:

    import-time  module- and class-level lines -- free on import
    body         lines inside a function       -- only run when called

Body coverage is the figure that moves when you write a test. Buckets come from
coverage.py's own per-function attribution (JSON format 3), not a re-parse, so
they always agree with `coverage report`.

Usage:
    APP_ENV=test uv run pytest --cov                     # produce .coverage
    uv run python scripts/coverage_body.py               # report
    uv run python scripts/coverage_body.py --fail-under 70
    uv run python scripts/coverage_body.py --markdown    # for a PR comment
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

import coverage
from coverage.exceptions import CoverageException

ROOT = Path(__file__).resolve().parent.parent

# Empty function name in coverage's JSON == module-level code (incl. class bodies).
MODULE_LEVEL = ""


def load_files(data_file: str | None, omit: list[str] | None) -> dict:
    """Render .coverage to JSON and return its per-file map."""
    # Only pass data_file when set: an explicit None disables it rather than defaulting.
    kwargs = {"data_file": data_file} if data_file else {}
    cov = coverage.Coverage(config_file=str(ROOT / ".coveragerc"), **kwargs)
    cov.load()
    # json_report replaces the file at this path, so hand it a name inside a temp
    # dir rather than an open NamedTemporaryFile.
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "coverage.json"
        try:
            cov.json_report(outfile=str(out), omit=omit, ignore_errors=True)
        except CoverageException:
            return {}
        return json.loads(out.read_text())["files"]


class Bucket:
    """Running totals for one bucket, scored the way coverage.py scores itself."""

    def __init__(self) -> None:
        self.stmts = self.covered = self.branches = self.covered_branches = self.partial = 0
        self.missing: list[int] = []

    def add(self, entry: dict) -> None:
        s = entry["summary"]
        self.stmts += s["num_statements"]
        self.covered += s["covered_lines"]
        self.branches += s["num_branches"]
        self.covered_branches += s["covered_branches"]
        self.partial += s["num_partial_branches"]
        self.missing += entry["missing_lines"]

    def merge(self, other: "Bucket") -> None:
        self.stmts += other.stmts
        self.covered += other.covered
        self.branches += other.branches
        self.covered_branches += other.covered_branches
        self.partial += other.partial

    @property
    def missed(self) -> int:
        return self.stmts - self.covered

    @property
    def total(self) -> int:
        return self.stmts + self.branches

    @property
    def cover(self) -> float | None:
        """Same formula as coverage.py: (lines + branch exits) taken over total."""
        if not self.total:
            return None
        return (self.covered + self.covered_branches) / self.total


def split(entries: dict) -> tuple[Bucket, Bucket]:
    """Partition a file's function entries into (import-time, body)."""
    imp, body = Bucket(), Bucket()
    for name, entry in entries.items():
        (imp if name == MODULE_LEVEL else body).add(entry)
    return imp, body


def ranges(lines: list[int]) -> str:
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'"""
    spans: list[list[int]] = []
    for line in sorted(set(lines)):
        if spans and line == spans[-1][1] + 1:
            spans[-1][1] = line
        else:
            spans.append([line, line])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def collect(files: dict) -> tuple[list[dict], Bucket, Bucket]:
    rows, imp_tot, body_tot = [], Bucket(), Bucket()
    for path, data in files.items():
        imp, body = split(data["functions"])
        imp_tot.merge(imp)
        body_tot.merge(body)
        rows.append({"path": path, "body": body, "headline": data["summary"]["percent_covered"] / 100})
    return rows, imp_tot, body_tot


def render_text(rows: list[dict], imp: Bucket, body: Bucket) -> None:
    w = max((len(r["path"]) for r in rows), default=20)
    print(f"{'Name':{w}} {'Stmts':>6} {'Miss':>5} {'Branch':>7} {'BrPart':>7} {'Body':>7} {'Headline':>9}  Missing")
    print("-" * (w + 60))
    for r in rows:
        b: Bucket = r["body"]
        cover = "-" if b.cover is None else f"{b.cover:.1%}"
        print(
            f"{r['path']:{w}} {b.stmts:>6} {b.missed:>5} {b.branches:>7} {b.partial:>7} "
            f"{cover:>7} {r['headline']:>9.1%}  {ranges(b.missing)}"
        )
    print("-" * (w + 60))
    combined = (imp.covered + imp.covered_branches + body.covered + body.covered_branches) / (imp.total + body.total)
    print(f"\n{'bucket':<14} {'covered':>9} {'total':>7} {'cover':>8}")
    for label, bucket in (("import-time", imp), ("body", body)):
        print(f"{label:<14} {bucket.covered + bucket.covered_branches:>9} {bucket.total:>7} {bucket.cover:>8.1%}")
    print(f"{'HEADLINE':<14} {'':>9} {imp.total + body.total:>7} {combined:>8.1%}")


def render_markdown(rows: list[dict], imp: Bucket, body: Bucket) -> None:
    print("| bucket | covered | total | cover |")
    print("| --- | --: | --: | --: |")
    for label, bucket in (("import-time (free on import)", imp), ("**function body**", body)):
        print(f"| {label} | {bucket.covered + bucket.covered_branches} | {bucket.total} | {bucket.cover:.1%} |")
    weak = sorted((r for r in rows if r["body"].cover is not None), key=lambda r: r["body"].cover)[:10]
    print("\n<details><summary>Weakest body coverage</summary>\n")
    print("| file | body cover | headline | missing |")
    print("| --- | --: | --: | --- |")
    for r in weak:
        print(f"| `{r['path']}` | {r['body'].cover:.1%} | {r['headline']:.1%} | {ranges(r['body'].missing) or '—'} |")
    print("\n</details>")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fail-under", type=float, metavar="PCT", help="exit 2 if body coverage is below PCT")
    p.add_argument("--markdown", action="store_true", help="emit a markdown table for PR comments")
    p.add_argument("--data-file", help="path to .coverage (default: config/cwd)")
    p.add_argument("--omit", action="append", help="glob to omit; repeatable")
    p.add_argument("--sort", choices=("cover", "name", "miss"), default="cover", help="row order (default: cover)")
    args = p.parse_args()

    files = load_files(args.data_file, args.omit)
    if not files:
        print("no coverage data -- run: APP_ENV=test uv run pytest --cov", file=sys.stderr)
        return 1

    rows, imp, body = collect(files)
    if args.sort == "name":
        rows.sort(key=lambda r: r["path"])
    elif args.sort == "miss":
        rows.sort(key=lambda r: -r["body"].missed)
    else:
        rows.sort(key=lambda r: (r["body"].cover if r["body"].cover is not None else 2, -r["body"].stmts))

    (render_markdown if args.markdown else render_text)(rows, imp, body)

    if args.fail_under is not None and body.cover is not None and body.cover * 100 < args.fail_under:
        print(f"\nFAIL: body coverage {body.cover:.1%} < {args.fail_under}%", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

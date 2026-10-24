"""Reuse the reviewed AppTest harness for the single anksi assignment change.

Run --phase before against an immutable pre-change snapshot, then --phase after
against the app under review. Reports describe local AppTest, not Cloud checks.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import traceback

SOURCE = (
    "Anksio anksia anksii ANKSIO anksi\n"
    "@anksio@ @anksia@ @anksii@ @anksi@\n"
    "angoro @angoro@ irigacio @irigacio@ tandemo @tandemo@ semajno @semajn@o\n"
    "mikrobiologio @mikrobiologi@o testikito orkidito\n"
    "trilobito sfinktero; grifelo brava frivola animalo\n"
    "%anksio% & du  spacoj"
)
CUSTOM_SOURCE = "anksio @anksio@ anksia anksii\nangoro irigacio tandemo semajno"


def configure(root):
    path = root / "tests/test_tril_sfinks_alcion_ui.py"
    spec = importlib.util.spec_from_file_location("anksi_reused_ui_harness", path)
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    harness.SOURCE = SOURCE
    harness.CUSTOM_SOURCE = CUSTOM_SOURCE
    harness.VALUES = {"anksi": ("忧虑", "忧ᴬᴷ")}
    harness.CONTROLS = {"angor": "忧", "irigaci": "水渠", "tandem": "串联",
                        "semajn": "周", "mikrobiologi": "微生ᴮᴼ学ᴸᴳ"}
    return harness


def aggregate(harness, report_dir):
    result = harness.aggregate_reports(report_dir)
    result["reused_harness_sha256"] = result["test_script_sha256"]
    result["test_script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["reviewed_values"] = harness.VALUES
    (report_dir / "app_ui_all.json").write_bytes(
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--before-root", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--language", choices=("JA", "ZH", "KO"))
    parser.add_argument("--phase", choices=("before", "after"))
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.before_root = args.before_root.resolve()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    harness = configure(args.root)
    if args.aggregate:
        result = aggregate(harness, args.report_dir)
        print(json.dumps({key: result[key] for key in
                          ("passed", "conversion_download_routes", "custom_upload_routes")}, indent=2))
        return
    if args.language:
        if args.phase is None:
            parser.error("--phase is required with --language")
        try:
            if args.phase == "before":
                result = harness.prepare_baseline(args.before_root, args.language)
            else:
                baseline = json.loads((args.report_dir / f"baseline_{args.language}.json").read_bytes())
                result = harness.run_ui(args.root, args.language, baseline, args.report_dir)
                result["scope"] = (
                    "Local AppTest only. anksi forms and @ capture; angor, irigaci, tandem, "
                    "semajn, mikro/bio/logi, trilobit and sfinkter controls; original annotations, "
                    "fixed legacy, protected text, spaces, line breaks, selected edition, "
                    "confirmed downloads and uploaded pre-change custom JSON."
                )
            result["reused_harness"] = "tests/test_tril_sfinks_alcion_ui.py"
            result["reviewed_values"] = harness.VALUES
            filename = (f"baseline_{args.language}.json" if args.phase == "before"
                        else f"app_ui_{args.language}.json")
            (args.report_dir / filename).write_bytes(
                (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        except Exception:
            (args.report_dir / f"failure_{args.language}_{args.phase}.txt").write_bytes(
                traceback.format_exc().encode("utf-8"))
            raise
        return
    for language in ("JA", "ZH", "KO"):
        for phase in ((args.phase,) if args.phase else ("before", "after")):
            command = [sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
                       "--root", str(args.root), "--before-root", str(args.before_root),
                       "--report-dir", str(args.report_dir), "--language", language, "--phase", phase]
            completed = subprocess.run(command, cwd=args.root, text=True, encoding="utf-8", capture_output=True)
            (args.report_dir / f"{language}_{phase}.log").write_bytes(
                (completed.stdout + completed.stderr).encode("utf-8"))
            if completed.returncode:
                raise RuntimeError((language, phase, completed.stdout[-1000:], completed.stderr[-3000:]))
            print(language, phase, "PASS", flush=True)
    if args.phase != "before":
        aggregate(harness, args.report_dir)


if __name__ == "__main__":
    main()

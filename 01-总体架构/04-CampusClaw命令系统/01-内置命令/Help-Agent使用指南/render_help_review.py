"""Render the Help projection with the existing Runtime presentation and examples."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT.parents[3] / "01-总体架构/01-CampusClaw多Agent运行时"
sys.path.insert(0, str(RUNTIME))

from render_chat_http_v1 import build_operation_html, validate_model, write_output
from help_review_projection import load_help_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    model = load_help_model()
    validate_model(model)
    output = ROOT / "help-review.html"
    content = build_operation_html([model])
    if args.check:
        if output.read_text(encoding="utf-8") != content:
            raise RuntimeError("Help HTML is stale")
    else:
        write_output(output, content)
    print(output)


if __name__ == "__main__":
    main()

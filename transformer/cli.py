"""Command-line interface for the transformer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from transformer.identity import IdentityResolver
from transformer.models.config import ProjectionConfig
from transformer.pipeline import CandidatePipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transform multi-source candidate data into canonical JSON.")
    parser.add_argument("--input", nargs="+", default=[], help="Input source files: CSV and/or GitHub JSON.")
    parser.add_argument("--github", nargs="+", default=[], help="GitHub usernames or profile URLs to fetch live.")
    parser.add_argument("--github-token", help="Optional GitHub API token. Defaults to GITHUB_TOKEN.")
    parser.add_argument("--config", help="Projection config JSON. Omit for default canonical output.")
    parser.add_argument("--id-map", help="Optional explicit identity mapping JSON.")
    parser.add_argument("--output", help="Optional output JSON path. Defaults to stdout.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = ProjectionConfig.from_file(args.config) if args.config else ProjectionConfig.default()
    identity = IdentityResolver.from_file(args.id_map)
    inputs = [Path(item) for item in args.input]
    github_token = args.github_token or os.getenv("GITHUB_TOKEN")

    if not inputs and not args.github:
        build_parser().error("Provide at least one --input file or --github username.")

    outputs = CandidatePipeline().run(
        inputs,
        config,
        identity,
        github_users=args.github,
        github_token=github_token,
    )
    payload = json.dumps(outputs, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

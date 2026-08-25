"""Experimental text-only router API. Not a validated routing decision."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from hecate.router.infer import (
    DEFAULT_THRESHOLD,
    RouterScorer,
    load_scorer,
    require_problem_statement,
)

_WARNING = "experimental — near-chance AUROC, see lab journal"

app = FastAPI(
    title="Hecate router v1 (experimental)",
    description=(
        "Internal/testing only. Grouped-by-repo AUROC is ~0.53 (near chance). "
        "Do not use this as a production routing decision."
    ),
    version="v1-experimental",
)
_scorer: RouterScorer | None = None
_default_threshold = DEFAULT_THRESHOLD


class RouteRequest(BaseModel):
    problem_statement: str
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class RouteResponse(BaseModel):
    p_small_resolves: float
    routing_decision: str
    model_version: str
    warning: str = _WARNING


def _gcs_blob(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"ROUTER_GCS_URI must start with gs://, got {uri!r}")
    rest = uri[5:]
    bucket, sep, blob = rest.partition("/")
    if not sep or not bucket or not blob:
        raise ValueError(f"invalid GCS URI: {uri}")
    return bucket, blob


def download_gcs_uri(uri: str, dest: Path) -> Path:
    from google.cloud import storage

    bucket_name, blob_name = _gcs_blob(uri)
    dest.parent.mkdir(parents=True, exist_ok=True)
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).download_to_filename(str(dest))
    return dest


def sibling_manifest_uri(head_uri: str) -> str:
    prefix, _, name = head_uri.rpartition("/")
    del name
    return f"{prefix}/manifest.json"


def load_runtime_scorer() -> RouterScorer:
    threshold_raw = os.environ.get("ROUTER_THRESHOLD", str(DEFAULT_THRESHOLD))
    global _default_threshold
    _default_threshold = float(threshold_raw)
    encoder_id = os.environ.get("ROUTER_ENCODER_ID") or None
    run_id = os.environ.get("ROUTER_RUN_ID") or None
    max_tokens = int(os.environ.get("ROUTER_MAX_TOKENS", "2048"))
    device = os.environ.get("ROUTER_DEVICE", "cpu")
    cache_dir = Path(os.environ.get("ROUTER_CACHE_DIR", "/tmp/hecate-router"))

    head_path = os.environ.get("ROUTER_HEAD_PATH")
    manifest_path = os.environ.get("ROUTER_MANIFEST_PATH")
    gcs_uri = os.environ.get("ROUTER_GCS_URI")

    if gcs_uri:
        local_head = cache_dir / "head_logreg.pt"
        local_manifest = cache_dir / "manifest.json"
        download_gcs_uri(gcs_uri, local_head)
        try:
            download_gcs_uri(sibling_manifest_uri(gcs_uri), local_manifest)
            manifest_path = str(local_manifest)
        except Exception:
            if not manifest_path:
                raise
        head_path = str(local_head)
    if not head_path:
        raise RuntimeError("set ROUTER_GCS_URI or ROUTER_HEAD_PATH")

    return load_scorer(
        head_path=head_path,
        manifest_path=manifest_path,
        encoder_id=encoder_id,
        run_id=run_id,
        max_tokens=max_tokens,
        device=device,
    )


@app.on_event("startup")
def _startup() -> None:
    global _scorer
    if os.environ.get("ROUTER_SKIP_LOAD") == "1":
        return
    _scorer = load_runtime_scorer()


@app.post("/v1-experimental/route", response_model=RouteResponse)
def route(body: RouteRequest) -> RouteResponse:
    try:
        require_problem_statement(body.problem_statement)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if _scorer is None:
        raise HTTPException(status_code=503, detail="router checkpoint is not loaded")
    threshold = (
        body.threshold if body.threshold is not None else _default_threshold
    )
    payload = _scorer.route(body.problem_statement, threshold=threshold)
    return RouteResponse(**payload)

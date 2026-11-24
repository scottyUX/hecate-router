"""Pinned log adapters. Original logs stay unchanged; evaluator files are not inputs."""

from __future__ import annotations
import json
import re
from pathlib import Path
from hecate.telemetry.events import Event, digest

ADAPTER_VERSION = "hecate.adapters.v1"


def read_jsonl(path):
    return [
        json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
    ]


class Emitter:
    def __init__(self, episode, identity, source):
        self.episode, self.identity, self.source = episode, identity, source
        self.events = []

    def emit(self, kind, payload, timestamp=None, quality=()):
        sequence = len(self.events)
        self.events.append(
            Event(
                self.episode,
                digest([self.episode, self.source, sequence]),
                sequence,
                kind,
                self.source,
                payload,
                timestamp,
                "unix" if timestamp is not None else None,
                identity=self.identity,
                quality=quality,
            )
        )


def controller(config, role):
    # Historical controller action availability is unknown, never invented.
    return {
        "active_model": role,
        "request_limit": config.get("limits", {}).get("task_model_requests"),
        "wall_limit_s": config.get("limits", {}).get("task_wall_s"),
        "context_limit": config.get("model", {}).get("context_tokens"),
    }


def usage_fields(usage):
    usage = usage or {}
    return {
        "input_tokens": usage.get("input_tokens", usage.get("prompt_tokens")),
        "output_tokens": usage.get("output_tokens", usage.get("completion_tokens")),
    }


def hecate_codex(
    agent: Path, *, episode_id: str, identity: dict, config: dict, role="m1"
):
    """Use replayed tool-result history at each request as its causal boundary.

    Codex event JSONL has no timestamps/correlation to gateway requests. Full
    Responses input histories do: use only completed function outputs already
    present in the next request, never zip the two logs by approximate timing.
    """
    emitter = Emitter(episode_id, identity, str(agent / "gateway.jsonl"))
    emitter.emit("controller", controller(config, role))
    metrics = {
        x["request"]: x
        for x in json.loads((agent / "result.json").read_text()).get(
            "usage_records", []
        )
    }
    records = read_jsonl(agent / "gateway.jsonl")
    requests = {x["request"] for x in records if x.get("event") == "request"}
    completed_responses = set()
    tools = set()
    starts = set()
    calls = {}
    for record in records:
        kind = record.get("event")
        number = record.get("request")
        ts = record.get("timestamp")
        if kind == "request":
            body = record.get("responses_request", {})
            if body.get("previous_response_id") or body.get("conversation"):
                raise ValueError("Stateful history cannot establish replay checkpoints")
            items = body.get("input", [])
            if not isinstance(items, list):
                items = []
            for item in items:
                if item.get("type") == "function_call":
                    calls[item["call_id"]] = item
                if item.get("type") != "function_call_output":
                    continue
                tool = item["call_id"]
                if tool in tools:
                    continue
                call = calls.get(tool)
                if not call:
                    raise ValueError("Tool output missing correlated call")
                if tool not in starts:
                    emitter.emit("tool_start", {"tool_id": tool}, ts)
                    starts.add(tool)
                output = item.get("output", "")
                if not isinstance(output, str):
                    raise ValueError("Unsupported tool-output format")
                # Trusted Codex envelope, not arbitrary command stdout.
                code = re.search(r"^Process exited with code (-?\d+)\s*$", output, re.M)
                session = re.search(r"^Process running with session ID ", output, re.M)
                if session:
                    continue  # async polling does not complete a command
                if code is None:
                    emitter.emit(
                        "legacy_step",
                        {"reason": "unknown_tool_completion"},
                        ts,
                        ("checkpoint_unverifiable",),
                    )
                    continue
                exit_code = int(code.group(1))
                emitter.emit(
                    "tool_complete",
                    {
                        "tool_id": tool,
                        "command": call.get("name") in {"exec_command", "write_stdin"},
                        "exit_code": exit_code,
                        "timeout": True if exit_code == 124 else None,
                        "error_text": None,
                    },
                    ts,
                )
                tools.add(tool)
            emitter.emit("boundary", {"verified": True}, ts)
            emitter.emit("model_request", {"request_id": str(number)}, ts)
        elif (
            kind in {"response", "upstream_response"}
            and number not in completed_responses
        ):
            # Successful response event is preferred; upstream_response also
            # preserves invalid model outputs in newer gateway versions.
            if kind == "upstream_response" and any(
                x.get("event") == "response" and x.get("request") == number
                for x in records
            ):
                continue
            metric = metrics.get(number, {})
            usage = (
                record.get("response", {}).get("usage")
                if kind == "response"
                else metric.get("usage")
            )
            payload = {
                "request_id": str(number),
                **usage_fields(usage),
                "attempts": metric["retries"] + 1 if "retries" in metric else None,
                "inference_s": metric.get("inference_wall_s"),
            }
            emitter.emit("model_response", payload, ts)
            completed_responses.add(number)
    # Old gateway failure records do not necessarily retain raw failed responses.
    # They cannot establish a safe request boundary and stay incomplete.
    emitter.emit(
        "termination",
        {
            "reason": json.loads((agent / "result.json").read_text()).get(
                "termination_reason", "unknown"
            )
        },
    )
    return emitter.events, {
        "adapter": ADAPTER_VERSION,
        "format": "hecate-codex-v1",
        "verified_boundaries": sum(e.kind == "boundary" for e in emitter.events),
        "missing_response_records": len(requests - completed_responses),
        "limitations": [
            "No historical controller action mask",
            "No structured visible tests or validated advisor scores",
            "Timeout flag unknown except explicit timeout exit124",
            "Tools completed after the last captured request are not inferred",
        ],
    }


def mini(agent: Path, *, episode_id: str, identity: dict, config: dict, role="m1"):
    emitter = Emitter(episode_id, identity, str(agent / "model.jsonl"))
    emitter.emit("controller", controller(config, role))
    seen = 0
    records = read_jsonl(agent / "model.jsonl")
    for record in records:
        observations = []
        previous = None
        for message in record.get("messages", []):
            text = message.get("content", "")
            if message.get("role") == "assistant":
                previous = text
            elif message.get("role") == "user" and previous:
                codes = re.match(r"\s*<returncode>(-?\d+)</returncode>", text)
                blocks = re.findall(r"```bash\n(.*?)\n```", previous, re.S)
                if codes and len(blocks) == 1:
                    observations.append(int(codes.group(1)))
                previous = None
        for index, code in enumerate(observations[seen:], seen):
            emitter.emit("tool_start", {"tool_id": str(index)})
            emitter.emit(
                "tool_complete",
                {
                    "tool_id": str(index),
                    "command": True,
                    "exit_code": code,
                    "timeout": None,
                },
            )
        if len(observations) < seen:
            raise ValueError("Mini history shrank; ordering unverifiable")
        seen = len(observations)
        emitter.emit("boundary", {"verified": True})
        emitter.emit("model_request", {"request_id": str(record["request"])})
        payload = {
            "request_id": str(record["request"]),
            **usage_fields(record.get("usage")),
            "inference_s": record.get("inference_wall_s"),
            "attempts": None,
        }
        emitter.emit("model_response", payload)
    emitter.emit("termination", {"reason": "saved_attempt_ended"})
    return emitter.events, {
        "adapter": ADAPTER_VERSION,
        "format": "hecate-mini-v1",
        "limitations": [
            "No event timestamps or verified transport-attempt count",
            "Native formatted observations only; no stdout test parsing",
            "No historical action mask",
        ],
    }


def e7_session(path: Path, *, episode_id: str, identity: dict, config: dict, role="m1"):
    """Legacy agent-server logging is coarse: no invented tool checkpoints."""
    emitter = Emitter(episode_id, identity, str(path))
    emitter.emit("controller", controller(config, role))
    for record in read_jsonl(path):
        kind = record.get("type")
        if kind == "initialization":
            emitter.emit(
                "controller",
                {"legacy_max_steps": record.get("max_steps")},
                quality=("checkpoint_unverifiable",),
            )
        elif kind == "advisor_feedback":
            emitter.emit("advisor_call", {"legacy_step": record.get("step")})
        elif kind == "step_completion":
            emitter.emit(
                "legacy_step",
                {
                    "legacy_step": record.get("step"),
                    "legacy_total_steps": record.get("total_agent_steps"),
                    "legacy_cost": record.get("cost"),
                    "actions": record.get("agent_actions", []),
                },
                quality=("checkpoint_unverifiable",),
            )
            if record.get("terminated"):
                emitter.emit("termination", {"reason": "legacy_terminated"})
                break
        else:
            raise ValueError("Unsupported E7 session log record")
    return emitter.events, {
        "adapter": ADAPTER_VERSION,
        "format": "e7-session-v1",
        "checkpoint_unverifiable": True,
        "limitations": [
            "Step batches do not identify individual correlated tool completions",
            "No request-level usage or safe checkpoint boundaries; no routing observations emitted",
        ],
    }


def e7_proxy(path: Path, *, episode_id: str, identity: dict, config: dict, role="m1"):
    emitter = Emitter(episode_id, identity, str(path))
    emitter.emit(
        "controller", controller(config, role), quality=("checkpoint_unverifiable",)
    )
    pending = None
    for record in read_jsonl(path):
        k = record.get("event")
        ts = record.get("t")
        if k == "request":
            pending = str(record["request"])
            emitter.emit("model_request", {"request_id": pending}, ts)
        elif k == "response" and pending:
            emitter.emit(
                "model_response",
                {
                    "request_id": pending,
                    **usage_fields(record.get("usage")),
                    "attempts": None,
                    "inference_s": None,
                },
                ts,
            )
            pending = None
        elif k == "advice":
            emitter.emit("advisor_call", {"request_id": str(record.get("request"))}, ts)
    return emitter.events, {
        "adapter": ADAPTER_VERSION,
        "format": "e7-proxy-v1",
        "checkpoint_unverifiable": True,
        "limitations": [
            "Proxy summary lacks correlated tool events; request count is not tool count"
        ],
    }

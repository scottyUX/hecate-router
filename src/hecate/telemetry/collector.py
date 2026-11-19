"""Streaming collector. Decisions are emitted only at verified request boundaries."""

from __future__ import annotations
from collections import deque
import math
import re
from hecate.telemetry.events import Event, digest


def ratio(a, b):
    return a / b if a is not None and isinstance(b, (float, int)) and b > 0 else None


class Collector:
    def __init__(self, config):
        self.config = config
        self.episodes = {}
        self.seen = {}

    def push(self, event: Event):
        key = (event.episode_id, event.event_id)
        fingerprint = digest(event.to_dict())
        if key in self.seen:
            if self.seen[key] != fingerprint:
                raise ValueError("Conflicting duplicate event")
            return None
        s = self.episodes.setdefault(
            event.episode_id,
            {
                "seq": -1,
                "requests": set(),
                "responses": {},
                "pending": set(),
                "tools": {},
                "window": deque(maxlen=self.config["command_window"]),
                "attempts": 0,
                "attempts_known": True,
                "advisor_calls": 0,
                "advisor_coverage": True,
                "emitted": 0,
                "terminated": False,
                "clock": None,
                "started": None,
                "elapsed": None,
                "time_valid": True,
                "last_time": None,
                "controller": {},
                "assessment": None,
                "tests": None,
                "test_delta": None,
                "identity": event.identity,
                "order_verified": True,
            },
        )
        if event.identity != s["identity"]:
            raise ValueError("Episode identity changed")
        if event.sequence <= s["seq"]:
            raise ValueError("Ambiguous episode event ordering")
        if s["terminated"]:
            raise ValueError("Events after episode termination")
        self.seen[key] = fingerprint
        s["seq"] = event.sequence
        if event.timestamp is not None:
            if s["clock"] is None:
                s["clock"] = event.clock
            if (
                event.kind == "controller"
                and event.payload.get("episode_start") is True
            ):
                s["started"] = event.timestamp
            if (
                not event.clock
                or event.clock != s["clock"]
                or (s["last_time"] is not None and event.timestamp < s["last_time"])
            ):
                s["time_valid"] = False
            s["last_time"] = event.timestamp
            s["elapsed"] = (
                event.timestamp - s["started"]
                if s["time_valid"] and s["started"] is not None
                else None
            )
        p = event.payload
        k = event.kind
        if "checkpoint_unverifiable" in event.quality:
            s["order_verified"] = False
        if k == "model_request":
            s["requests"].add(p["request_id"])
        elif k in {"model_response", "model_failure"}:
            request = p["request_id"]
            if request not in s["requests"]:
                raise ValueError("Response without request")
            if request in s["responses"]:
                if s["responses"][request] == p:
                    return None
                raise ValueError("Conflicting response correlation")
            s["responses"][request] = p
            attempts = p.get("attempts")
            if attempts is None:
                s["attempts_known"] = False
            else:
                s["attempts"] += attempts
        elif k == "tool_start":
            tool = p["tool_id"]
            if tool not in s["tools"]:
                s["pending"].add(tool)
        elif k == "tool_complete":
            tool = p["tool_id"]
            if tool in s["tools"]:
                if s["tools"][tool] != p:
                    raise ValueError("Conflicting tool completion")
                return None
            if tool not in s["pending"] and p.get("start_verified", True):
                raise ValueError("Completion without tool start")
            s["pending"].discard(tool)
            if tool not in s["tools"]:
                s["tools"][tool] = p
                if p.get("command", False):
                    code = p.get("exit_code")
                    signature = None
                    if code is not None and code != 0:
                        text = p.get("error_text")
                        if text:
                            signature = re.sub(r"\s+", " ", text).strip()
                    s["window"].append(
                        {
                            "exit": code,
                            "timeout": p.get("timeout"),
                            "signature": signature,
                        }
                    )
        elif k == "advisor_call":
            s["advisor_calls"] += 1
        elif k == "legacy_step":
            s["advisor_coverage"] = False
        elif k == "advisor_assessment":
            s["assessment"] = (len(s["tools"]), p)
        elif k == "controller":
            s["controller"].update(p)
        elif k == "visible_tests":
            tests = p.get("tests", {})
            context = (
                p.get("selection_id"),
                p.get("conditions_id"),
                p.get("parser_version"),
            )
            valid = (
                bool(tests)
                and all(context)
                and all(v in {"passed", "failed"} for v in tests.values())
            )
            previous = s["tests"]
            s["test_delta"] = None
            if valid:
                if (
                    previous
                    and previous[0] == context
                    and previous[1].keys() == tests.keys()
                ):
                    s["test_delta"] = sum(v == "passed" for v in tests.values()) - sum(
                        v == "passed" for v in previous[1].values()
                    )
                s["tests"] = (context, tests)
            else:
                s["tests"] = None
        elif k == "termination":
            s["terminated"] = True
        elif k == "boundary":
            completed = len(s["tools"])
            if (
                not p.get("verified")
                or not s["order_verified"]
                or s["pending"]
                or set(s["responses"]) != s["requests"]
            ):
                return None
            if completed - s["emitted"] >= self.config["cadence"]:
                s["emitted"] = completed
                return self.observation(event, s)
        return None

    def observation(self, event, s):
        values = {name: None for name in self.config["features"]}
        c = s["controller"]
        n = len(s["tools"])
        w = list(s["window"])
        values.update(
            completed_interactions=n,
            model_requests=len(s["requests"]),
            transport_attempts=s["attempts"] if s["attempts_known"] else None,
            advisor_calls=s["advisor_calls"] if s["advisor_coverage"] else None,
            request_budget_used=ratio(len(s["requests"]), c.get("request_limit")),
            elapsed_s=s["elapsed"],
            time_budget_used=ratio(s["elapsed"], c.get("wall_limit_s")),
        )
        if w and all(x["exit"] is not None for x in w):
            values["command_failure_rate"] = sum(x["exit"] != 0 for x in w) / len(w)
        if w and all(x["timeout"] is not None for x in w):
            values["command_timeouts"] = sum(x["timeout"] for x in w)
        failed = [x for x in w if x["exit"] != 0]
        if (
            w
            and all(x["exit"] is not None for x in w)
            and all(x["signature"] for x in failed)
        ):
            signatures = [x["signature"] for x in failed]
            values["repeated_errors"] = len(signatures) - len(set(signatures))
        if s["tests"]:
            statuses = s["tests"][1].values()
            values.update(
                visible_passed=sum(x == "passed" for x in statuses),
                visible_failed=sum(x == "failed" for x in statuses),
                visible_pass_delta=s["test_delta"],
            )
        responses = list(s["responses"].values())
        complete = bool(responses) and len(responses) == len(s["requests"])
        for field, feature in [
            ("input_tokens", "input_tokens"),
            ("output_tokens", "output_tokens"),
            ("inference_s", "inference_s"),
        ]:
            if complete and all(
                isinstance(x.get(field), (int, float))
                and math.isfinite(x[field])
                and x[field] >= 0
                for x in responses
            ):
                values[feature] = sum(x[field] for x in responses)
        if responses:
            values["context_used"] = ratio(
                responses[-1].get("input_tokens"), c.get("context_limit")
            )
        if c.get("active_model") in {"m1", "m2"}:
            values["active_model_m2"] = int(c["active_model"] == "m2")
        assessment = s["assessment"]
        if (
            assessment
            and n - assessment[0] <= self.config["advisor_max_age_interactions"]
            and assessment[1].get("validated") is True
            and assessment[1].get("schema") == "hecate.assessment.v1"
        ):
            for name in ["progress", "stuckness", "remaining_difficulty", "confidence"]:
                value = assessment[1].get(name)
                if (
                    isinstance(value, (int, float))
                    and math.isfinite(value)
                    and 0 <= value <= 1
                ):
                    values["advisor_" + name] = value
        action = c.get("action_mask")
        if action is not None and (
            len(action) != 2
            or any(type(x) is not bool for x in action)
            or not any(action)
        ):
            raise ValueError("Invalid action mask")
        return {
            "episode_id": event.episode_id,
            "checkpoint_id": event.event_id,
            "sequence": event.sequence,
            "identity": event.identity,
            "source": event.source,
            "features": values,
            "action_mask": action,
            "clock": s["clock"],
            "checkpoint_verified": True,
        }


def collect(events, config):
    collector = Collector(config)
    observations = []
    for event in events:
        row = collector.push(event)
        if row is not None:
            observations.append(row)
    return observations

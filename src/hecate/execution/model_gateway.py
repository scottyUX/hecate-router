"""Local Codex Responses → vLLM Chat adapter; never executes model tools.

Reuses the request-cap/accounting pattern of advisor-models' E7 CodexProxy,
not its OpenRouter forwarding, advice insertion, host networking or price model.
The upstream response is buffered and validated before exposing any SSE event,
so transport retries cannot replay tools which Codex has already executed.
"""
from __future__ import annotations

import copy
import json
import shlex
import socketserver
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx


class ProtocolError(ValueError):
    pass


class ModelOutputError(ProtocolError):
    """A model response was received but did not yield a valid action."""


class OutputBudgetExceeded(ModelOutputError):
    """Generation exhausted the fixed output-token budget."""


ALLOWED_TOOLS = {
    "exec_command",
    "write_stdin",
    "shell",
    "shell_command",
    "apply_patch",
    "update_plan",
}


def text_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if any(
            p.get("type") not in {"input_text", "output_text", "text"} for p in value
        ):
            raise ProtocolError("Only text content is supported")
        return "\n".join(p.get("text", "") for p in value)
    if value is None:
        return ""
    raise ProtocolError("Invalid message content")


def translate_request(
    body: dict,
    model: str,
    sampling: dict,
    tool_decoding: str = "auto",
    editing_mode: str = "patch",
) -> tuple[dict, dict]:
    if editing_mode not in {"patch", "shell"}:
        raise ProtocolError("Unknown editing mode")
    if body.get("previous_response_id") or body.get("conversation"):
        raise ProtocolError(
            "Server-side history is unsupported; Codex must resend full history"
        )
    if body.get("reasoning", {}).get("effort") not in (None, "none"):
        raise ProtocolError("Qwen2.5-Coder is configured without reasoning")
    messages = []
    if body.get("instructions"):
        messages.append({"role": "system", "content": body["instructions"]})
    items = body.get("input", [])
    if isinstance(items, str):
        items = [{"type": "message", "role": "user", "content": items}]
    custom, tools, removed = {}, [], []
    for tool in body.get("tools", []):
        name = tool.get("name")
        if name not in ALLOWED_TOOLS or (
            name == "apply_patch" and editing_mode == "shell"
        ):
            removed.append(name or tool.get("type"))
            continue
        if tool.get("type") == "function":
            fn = {
                k: copy.deepcopy(tool[k])
                for k in ("name", "description", "parameters")
                if k in tool
            }
        elif tool.get("type") == "custom" and name == "apply_patch":
            custom[name] = True
            fn = {
                "name": name,
                "description": tool.get("description", "Apply a patch")
                + " Supply the complete patch as the input JSON string.",
                "parameters": {
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"],
                    "additionalProperties": False,
                },
            }
        else:
            raise ProtocolError(f"Unsupported tool contract: {name}")
        if name in {"exec_command", "shell", "shell_command"}:
            # The external Docker boundary is fixed: escalation is not an action.
            params = fn.get("parameters", {})
            for key in ("sandbox_permissions", "justification", "prefix_rule"):
                params.get("properties", {}).pop(key, None)
                if key in params.get("required", []):
                    params["required"].remove(key)
            params["additionalProperties"] = False
        tools.append({"type": "function", "function": fn})
    pending = set()
    for item in items:
        kind = item.get("type", "message")
        if kind == "message":
            if pending:
                raise ProtocolError("Message before pending tool outputs")
            role = item.get("role", "user")
            if role not in {"system", "developer", "user", "assistant"}:
                raise ProtocolError("Unsupported role")
            messages.append(
                {
                    "role": "system" if role == "developer" else role,
                    "content": text_content(item.get("content")),
                }
            )
        elif kind in {"function_call", "custom_tool_call"}:
            name, call_id = item["name"], item["call_id"]
            args = (
                item.get("arguments", "{}")
                if kind == "function_call"
                else json.dumps({"input": item["input"]})
            )
            if name not in ALLOWED_TOOLS or call_id in pending:
                raise ProtocolError("Unsupported tool or duplicate call ID")
            json.loads(args)
            call = {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": args},
            }
            if messages and messages[-1].get("tool_calls"):
                messages[-1]["tool_calls"].append(call)
            else:
                messages.append(
                    {"role": "assistant", "content": None, "tool_calls": [call]}
                )
            pending.add(call_id)
        elif kind in {"function_call_output", "custom_tool_call_output"}:
            if item["call_id"] not in pending:
                raise ProtocolError("Tool output without matching call")
            pending.remove(item["call_id"])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item["call_id"],
                    "content": text_content(item.get("output")),
                }
            )
        else:
            raise ProtocolError(f"Unsupported history item: {kind}")
    if pending:
        raise ProtocolError("Missing tool outputs")
    if tool_decoding not in {"auto", "required_with_finish"}:
        raise ProtocolError("Unknown tool decoding mode")
    if tool_decoding == "required_with_finish":
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "hecate_finish",
                    "description": "End the coding session ONLY after completing the requested actions and observing their results. Provide your final report.",
                    "parameters": {
                        "type": "object",
                        "properties": {"response": {"type": "string"}},
                        "required": ["response"],
                        "additionalProperties": False,
                    },
                },
            }
        )
    payload = {"model": model, "messages": messages, "stream": False, **sampling}
    if tools:
        payload.update(
            tools=tools,
            tool_choice="required"
            if tool_decoding == "required_with_finish"
            else "auto",
            parallel_tool_calls=False,
        )
    return payload, {
        "custom": custom,
        "allowed": [t["function"]["name"] for t in tools],
        "removed": removed,
    }


def translate_response(raw: dict, contract: dict, command_timeout_s: int = 120) -> dict:
    choices = raw.get("choices") or []
    if len(choices) != 1:
        raise ModelOutputError("Missing or ambiguous completion")
    if choices[0].get("finish_reason") == "length":
        raise OutputBudgetExceeded("Model exhausted its fixed output-token budget")
    if choices[0].get("finish_reason") not in {"stop", "tool_calls"}:
        raise ModelOutputError("Unsupported model completion reason")
    message = choices[0]["message"]
    output = []
    if message.get("content"):
        output.append(
            {
                "id": "msg_" + uuid.uuid4().hex,
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": message["content"],
                        "annotations": [],
                    }
                ],
            }
        )
    seen = set()
    calls = message.get("tool_calls") or []
    if any(c["function"]["name"] == "hecate_finish" for c in calls):
        if "hecate_finish" not in contract["allowed"]:
            raise ProtocolError("Finish action not advertised")
        if len(calls) != 1 or message.get("content"):
            raise ProtocolError("Finish must be a sole action")
        value = json.loads(calls[0]["function"]["arguments"])
        if set(value) != {"response"} or not isinstance(value["response"], str):
            raise ProtocolError("Invalid finish response")
        output.append(
            {
                "id": "msg_" + uuid.uuid4().hex,
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": value["response"],
                        "annotations": [],
                    }
                ],
            }
        )
        calls = []
    for call in calls:
        name, args = call["function"]["name"], call["function"]["arguments"]
        if name not in contract["allowed"]:
            raise ProtocolError(f"Model called unadvertised tool: {name}")
        call_id = call.get("id") or "call_" + uuid.uuid4().hex
        if call_id in seen:
            raise ProtocolError("Duplicate generated call ID")
        seen.add(call_id)
        value = json.loads(args)
        if not isinstance(value, dict):
            raise ProtocolError("Tool arguments must be a JSON object")
        if name in contract["custom"]:
            if set(value) != {"input"} or not isinstance(value["input"], str):
                raise ProtocolError(
                    "Custom patch tool requires exactly one input string"
                )
            output.append(
                {
                    "id": "ct_" + uuid.uuid4().hex,
                    "type": "custom_tool_call",
                    "status": "completed",
                    "call_id": call_id,
                    "name": name,
                    "input": value["input"],
                }
            )
        else:
            if value.get("sandbox_permissions") == "require_escalated":
                raise ProtocolError("Sandbox escalation is unavailable")
            if name == "exec_command":
                if not isinstance(value.get("cmd"), str):
                    raise ProtocolError("exec_command requires cmd")
                value["cmd"] = (
                    f"timeout --signal=TERM --kill-after=5s {command_timeout_s}s bash -lc "
                    + shlex.quote(value["cmd"])
                )
            elif name == "shell_command":
                value["timeout_ms"] = min(
                    int(value.get("timeout_ms", command_timeout_s * 1000)),
                    command_timeout_s * 1000,
                )
            output.append(
                {
                    "id": "fc_" + uuid.uuid4().hex,
                    "type": "function_call",
                    "status": "completed",
                    "call_id": call_id,
                    "name": name,
                    "arguments": json.dumps(value),
                }
            )
    if not output:
        raise ProtocolError("Empty model response")
    usage = raw.get("usage")
    mapped = (
        None
        if usage is None
        else {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }
    )
    return {
        "id": "resp_" + uuid.uuid4().hex,
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": raw.get("model"),
        "output": output,
        "usage": mapped,
        "error": None,
        "incomplete_details": None,
    }


def response_events(response: dict) -> bytes:
    """Responses SSE; completed output carries all validated buffered arguments."""
    events = []

    def add(kind: str, **fields: Any) -> None:
        event = {"type": kind, "sequence_number": len(events), **fields}
        events.append(f"event: {kind}\ndata: {json.dumps(event)}\n\n")

    initial = {**response, "status": "in_progress", "output": []}
    add("response.created", response=initial)
    add("response.in_progress", response=initial)
    for index, item in enumerate(response["output"]):
        start = {**item, "status": "in_progress"}
        if item["type"] == "message":
            start["content"] = []
        if item["type"] == "function_call":
            start["arguments"] = ""
        if item["type"] == "custom_tool_call":
            start["input"] = ""
        add("response.output_item.added", output_index=index, item=start)
        if item["type"] == "message":
            text = item["content"][0]["text"]
            add(
                "response.content_part.added",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                part={"type": "output_text", "text": "", "annotations": []},
            )
            add(
                "response.output_text.delta",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                delta=text,
            )
            add(
                "response.output_text.done",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                text=text,
            )
            add(
                "response.content_part.done",
                item_id=item["id"],
                output_index=index,
                content_index=0,
                part=item["content"][0],
            )
        else:
            field = "input" if item["type"] == "custom_tool_call" else "arguments"
            prefix = (
                "response.custom_tool_call_input"
                if field == "input"
                else "response.function_call_arguments"
            )
            # Deliberate chunking exercises consumers with fragmented JSON/patch text.
            value = item[field]
            for off in range(0, len(value), 64):
                add(
                    prefix + ".delta",
                    item_id=item["id"],
                    output_index=index,
                    delta=value[off : off + 64],
                )
            add(
                prefix + ".done",
                item_id=item["id"],
                output_index=index,
                **{field: value},
            )
        add("response.output_item.done", output_index=index, item=item)
    add("response.completed", response=response)
    return "".join(events).encode()


def failure_kind(exc: Exception, *, cap_hit: bool = False) -> str:
    if cap_hit:
        return "request_budget_exhausted"
    if isinstance(exc, OutputBudgetExceeded):
        return "model_output_budget_exhausted"
    if isinstance(exc, ModelOutputError):
        return "model_output_failure"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 400:
        # Only explicit length errors qualify; unrelated HTTP400 remains an error.
        text = exc.response.text.lower()
        if any(s in text for s in (
            "maximum context length", "context_length_exceeded",
            "context length exceeded", "max_model_len", "maximum model length",
        )):
            return "context_budget_exhausted"
    return (
        "tool_protocol_failure"
        if isinstance(exc, (ProtocolError, ValueError, KeyError))
        else "model_server_failure"
    )


class Gateway:
    """Unix-only ingress. Fixed loopback upstream; no auth/header forwarding."""

    def __init__(
        self,
        socket_path: Path,
        upstream: str,
        model: str,
        log_dir: Path,
        *,
        request_limit: int,
        sampling: dict,
        timeout_s: int = 180,
        retries: int = 2,
        command_timeout_s: int = 120,
        transport: Callable | None = None,
        tool_decoding: str = "auto",
        editing_mode: str = "patch",
    ):
        parsed = urlparse(upstream)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Upstream must be a credential-free local HTTP endpoint")
        self.socket_path, self.upstream, self.model, self.log_dir = (
            socket_path,
            upstream.rstrip("/"),
            model,
            log_dir,
        )
        (
            self.request_limit,
            self.sampling,
            self.timeout_s,
            self.retries,
            self.command_timeout_s,
        ) = (request_limit, sampling, timeout_s, retries, command_timeout_s)
        self.editing_mode = editing_mode
        self.tool_decoding = tool_decoding
        self.transport = transport
        self.requests = 0
        self.cap_hit = False
        self.failed = False
        self.failure_kind = None
        self.lock = threading.Lock()
        self.metrics = []
        self.original_calls = {}

    def record(self, value: dict) -> None:
        with (self.log_dir / "gateway.jsonl").open("a") as f:
            f.write(json.dumps({"timestamp": time.time(), **value}) + "\n")

    def complete(self, body: dict) -> dict:
        with self.lock:
            if self.failed:
                raise ProtocolError("Session has a prior gateway failure")
            if self.requests >= self.request_limit:
                self.cap_hit = True
                raise ProtocolError("Model request budget exhausted")
            self.requests += 1
            request_id = self.requests
        upstream_body = copy.deepcopy(body)
        if isinstance(upstream_body.get("input"), list):
            for item in upstream_body["input"]:
                if (
                    item.get("type") == "function_call"
                    and item.get("call_id") in self.original_calls
                ):
                    item["arguments"] = self.original_calls[item["call_id"]]
        payload, contract = translate_request(
            upstream_body,
            self.model,
            self.sampling,
            self.tool_decoding,
            self.editing_mode,
        )
        self.record(
            {
                "event": "request",
                "request": request_id,
                "responses_request": body,
                "effective_chat_request": payload,
                "tool_contract": contract,
            }
        )
        started = time.monotonic()
        for attempt in range(self.retries + 1):
            try:
                raw = self.transport(payload) if self.transport else self._post(payload)
                # Preserve unsuccessful model output as well as successful actions.
                self.record(
                    {
                        "event": "upstream_response",
                        "request": request_id,
                        "response": raw,
                    }
                )
                try:
                    result = translate_response(raw, contract, self.command_timeout_s)
                except (ProtocolError, ValueError, KeyError, TypeError) as exc:
                    usage = raw.get("usage") or {}
                    mapped = (
                        None
                        if not usage
                        else {
                            "input_tokens": usage.get("prompt_tokens"),
                            "output_tokens": usage.get("completion_tokens"),
                            "total_tokens": usage.get("total_tokens"),
                        }
                    )
                    self.metrics.append(
                        {
                            "request": request_id,
                            "retries": attempt,
                            "inference_wall_s": time.monotonic() - started,
                            "usage": mapped,
                            "failed": True,
                        }
                    )
                    if isinstance(exc, ModelOutputError):
                        raise
                    raise ModelOutputError(str(exc)) from exc
                for call in (
                    raw.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
                ):
                    if call.get("id"):
                        self.original_calls[call["id"]] = call["function"]["arguments"]
                self.record(
                    {
                        "event": "response",
                        "request": request_id,
                        "response": result,
                        "upstream_response": raw,
                    }
                )
                self.metrics.append(
                    {
                        "request": request_id,
                        "retries": attempt,
                        "inference_wall_s": time.monotonic() - started,
                        "usage": result["usage"],
                    }
                )
                return result
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                retryable = not isinstance(
                    exc, httpx.HTTPStatusError
                ) or exc.response.status_code in {408, 429, 500, 502, 503, 504}
                self.record(
                    {
                        "event": "upstream_failure",
                        "request": request_id,
                        "attempt": attempt + 1,
                        "type": type(exc).__name__,
                        "status": exc.response.status_code
                        if isinstance(exc, httpx.HTTPStatusError)
                        else None,
                        "failure_kind": failure_kind(exc),
                        "response_body": exc.response.text[:2000]
                        if isinstance(exc, httpx.HTTPStatusError) else None,
                    }
                )
                if attempt >= self.retries or not retryable:
                    self.metrics.append(
                        {
                            "request": request_id,
                            "retries": attempt,
                            "inference_wall_s": time.monotonic() - started,
                            "usage": None,
                            "failed": True,
                        }
                    )
                    raise
                time.sleep(min(2**attempt, 4))
        raise AssertionError("unreachable")

    def _post(self, payload: dict) -> dict:
        with httpx.Client(timeout=self.timeout_s, trust_env=False) as client:
            response = client.post(self.upstream + "/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()

    def __enter__(self):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                code = 200
                try:
                    if self.path != "/v1/responses":
                        raise ProtocolError("Unsupported path")
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 16 * 1024 * 1024:
                        raise ProtocolError("Invalid request size")
                    body = json.loads(self.rfile.read(size))
                    out = owner.complete(body)
                    data = (
                        response_events(out)
                        if body.get("stream")
                        else json.dumps(out).encode()
                    )
                    content = (
                        "text/event-stream"
                        if body.get("stream")
                        else "application/json"
                    )
                except Exception as exc:
                    owner.failed = not owner.cap_hit
                    owner.failure_kind = failure_kind(exc, cap_hit=owner.cap_hit)
                    owner.record(
                        {
                            "event": "gateway_error",
                            "type": type(exc).__name__,
                            "message": str(exc)[:500],
                            "failure_kind": owner.failure_kind,
                        }
                    )
                    code = 400 if isinstance(exc, ProtocolError) else 502
                    data = json.dumps(
                        {
                            "error": {
                                "message": str(exc)[:500],
                                "type": "invalid_request_error",
                            }
                        }
                    ).encode()
                    content = "application/json"
                self.send_response(code)
                self.send_header("Content-Type", content)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
            daemon_threads = True

        self.server = Server(str(self.socket_path), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.socket_path.unlink(missing_ok=True)

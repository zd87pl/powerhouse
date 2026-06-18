"""Heuristic error-diagnosis engine.

Turns a raw error (title + message + stack trace) into a structured triage:
root cause, severity, concrete fix steps, and the files most likely involved.

This is the deterministic, dependency-free core of Powerhouse's autofix loop.
It runs with no API keys so the capability is demoable out of the box, and it
doubles as the fallback when an LLM-backed diagnosis is unavailable — the same
pattern the intent parser uses (``_fallback_parse``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Diagnosis:
    """Structured triage for a single error."""

    category: str
    severity: str  # high | medium | low
    summary: str
    root_cause: str
    suggested_fix: list[str] = field(default_factory=list)
    likely_files: list[str] = field(default_factory=list)
    confidence: str = "medium"  # high | medium | low
    source: str = "heuristic"  # heuristic | llm

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "summary": self.summary,
            "root_cause": self.root_cause,
            "suggested_fix": list(self.suggested_fix),
            "likely_files": list(self.likely_files),
            "confidence": self.confidence,
            "source": self.source,
        }

    def format_text(self) -> str:
        """Render a human-readable summary (used for agent-run output)."""
        lines = [
            f"[{self.severity.upper()}] {self.summary}",
            "",
            f"Root cause: {self.root_cause}",
        ]
        if self.suggested_fix:
            lines.append("")
            lines.append("Suggested fix:")
            lines.extend(
                f"  {i}. {step}" for i, step in enumerate(self.suggested_fix, 1)
            )
        if self.likely_files:
            lines.append("")
            lines.append("Likely files: " + ", ".join(self.likely_files))
        lines.append("")
        lines.append(f"(category={self.category}, confidence={self.confidence})")
        return "\n".join(lines)


# ── File extraction ───────────────────────────────────────────────────────────

# Python tracebacks:  File "path/to/file.py", line 42, in func
_PY_FRAME = re.compile(r'File "([^"]+)", line (\d+)')
# JS/TS stacks:  at fn (path/to/file.tsx:12:5)  /  path/to/file.ts:12:5
_JS_FRAME = re.compile(r"([\w./@\-]+\.(?:tsx?|jsx?|mjs|cjs)):(\d+)(?::\d+)?")


def extract_files(text: str, limit: int = 5) -> list[str]:
    """Pull the most relevant ``path:line`` references out of a stack trace."""
    found: list[str] = []
    for match in _PY_FRAME.finditer(text):
        found.append(f"{match.group(1)}:{match.group(2)}")
    for match in _JS_FRAME.finditer(text):
        found.append(f"{match.group(1)}:{match.group(2)}")

    seen: set[str] = set()
    ordered: list[str] = []
    for ref in found:
        # Skip noise from third-party/runtime frames where the fix won't live.
        if "/node_modules/" in ref or "/site-packages/" in ref:
            continue
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    if not ordered:
        # Fall back to including dependency frames rather than nothing.
        for ref in found:
            if ref not in seen:
                seen.add(ref)
                ordered.append(ref)
    return ordered[:limit]


# ── Rule table ─────────────────────────────────────────────────────────────────


@dataclass
class _Rule:
    pattern: re.Pattern
    category: str
    severity: str
    summary: str
    root_cause: str
    suggested_fix: list[str]
    confidence: str = "high"


def _r(pattern: str, *args, **kwargs) -> _Rule:
    return _Rule(re.compile(pattern, re.IGNORECASE), *args, **kwargs)


# Ordered most-specific → least-specific. The first match wins, so narrow
# patterns (NoneType attribute access) must precede broad ones (AttributeError).
_RULES: list[_Rule] = [
    _r(
        r"(?:ModuleNotFoundError|ImportError).*?No module named ['\"]?([\w.]+)",
        "missing_dependency",
        "high",
        "A required module ('{name}') is not installed or not importable.",
        "Python can't import '{name}'. The package is missing from the environment, "
        "or the import path is wrong.",
        [
            "Add '{name}' to requirements.txt and reinstall (pip install -r requirements.txt).",
            "If '{name}' is a local module, check it's on PYTHONPATH and the package has an __init__.py.",
            "Verify the import name matches the installed distribution name.",
        ],
    ),
    _r(
        r"ImportError: cannot import name ['\"]?(\w+)",
        "import_error",
        "high",
        "An imported name ('{name}') does not exist in the target module.",
        "'{name}' was renamed, removed, or never existed in the module being imported from.",
        [
            "Check the module's current API for the correct name of '{name}'.",
            "Watch for circular imports — a half-initialised module exposes fewer names.",
            "Pin or upgrade the dependency if '{name}' moved between versions.",
        ],
    ),
    _r(
        r"AttributeError:.*?['\"]?NoneType['\"]? object has no attribute ['\"]?(\w+)",
        "null_reference",
        "high",
        "Called '.{name}' on a value that was None.",
        "Something expected an object but got None — usually a lookup that returned "
        "nothing or an uninitialised variable.",
        [
            "Trace where the None originates (a failed query, missing key, or skipped assignment).",
            "Guard the access: check `if value is not None:` before reading '.{name}'.",
            "Return an explicit default instead of None upstream where it makes sense.",
        ],
    ),
    _r(
        r"AttributeError:.*object has no attribute ['\"]?(\w+)",
        "attribute_error",
        "medium",
        "Accessed an attribute ('{name}') the object doesn't have.",
        "The object is a different type than expected, or '{name}' is a typo.",
        [
            "Confirm the object's actual type at the failure point.",
            "Check '{name}' for typos and that it matches the current class definition.",
        ],
    ),
    _r(
        r"KeyError: ['\"]?([\w .\-]+)",
        "missing_key",
        "medium",
        "Looked up a dictionary key ('{name}') that wasn't present.",
        "The input data is missing the '{name}' field, or it's spelled differently.",
        [
            "Use dict.get('{name}') with a default instead of indexing.",
            "Validate the payload shape before access (e.g. with a Pydantic model).",
            "Log the actual keys to confirm what the data really contains.",
        ],
    ),
    _r(
        r"NameError: name ['\"]?(\w+)['\"]? is not defined",
        "undefined_name",
        "high",
        "Referenced a name ('{name}') that isn't defined in scope.",
        "'{name}' is misspelled, defined later, or its import is missing.",
        [
            "Add the missing import or definition for '{name}'.",
            "Check for a typo or a name used before it's assigned.",
        ],
    ),
    _r(
        r"IndexError",
        "index_out_of_range",
        "medium",
        "Indexed a sequence out of its bounds.",
        "Code assumed a list/tuple had more elements than it did.",
        [
            "Check the length before indexing, or iterate instead of using fixed indices.",
            "Handle the empty/short-collection case explicitly.",
        ],
    ),
    _r(
        r"(?:TypeError: )?Cannot read propert(?:y|ies) of (?:undefined|null)(?:.*reading ['\"]?(\w+)['\"]?)?",
        "null_reference",
        "high",
        "Read a property ('{name}') off undefined/null.",
        "A value wasn't loaded yet (async/props) or a lookup returned nothing.",
        [
            "Use optional chaining (obj?.{name}) and a sensible default.",
            "Render a loading/empty state until the data is available.",
            "Trace where the undefined value is produced upstream.",
        ],
    ),
    _r(
        r"TypeError:.*positional argument",
        "type_error",
        "medium",
        "A function was called with the wrong number of arguments.",
        "The call site and the function signature have drifted apart.",
        [
            "Compare the call with the current function signature.",
            "Update all call sites if the signature changed.",
        ],
    ),
    _r(
        r"TypeError",
        "type_error",
        "medium",
        "An operation received a value of an unexpected type.",
        "A value is a different type than the code assumes (e.g. str vs int, None vs object).",
        [
            "Inspect the types flowing into the failing operation.",
            "Coerce or validate inputs at the boundary before use.",
        ],
    ),
    _r(
        r"(?:FileNotFoundError|No such file or directory|ENOENT)",
        "file_not_found",
        "medium",
        "A file or path the code expected does not exist.",
        "A path is wrong, relative to the wrong working directory, or the file was never created.",
        [
            "Log and verify the absolute path being opened.",
            "Create the file/directory first, or guard with an existence check.",
            "Avoid relying on the process working directory — resolve paths explicitly.",
        ],
    ),
    _r(
        r"(?:PermissionError|EACCES|Permission denied)",
        "permission_denied",
        "medium",
        "The process lacks permission for a file or resource.",
        "File ownership/mode or a restricted directory is blocking the operation.",
        [
            "Check the file ownership and mode against the runtime user.",
            "Write to a path the process can access (e.g. a temp dir) instead.",
        ],
    ),
    _r(
        r"(?:ConnectionRefusedError|ECONNREFUSED|Connection refused)",
        "connection_refused",
        "high",
        "A network connection was refused by the target service.",
        "The dependency (DB, API, cache) is down, not started, or on a different host/port.",
        [
            "Confirm the service is running and reachable at the configured host:port.",
            "Check the connection string / env var for the right address.",
            "Add a startup readiness check and a retry-with-backoff around the call.",
        ],
    ),
    _r(
        r"(?:ReadTimeout|ConnectTimeout|TimeoutError|ETIMEDOUT|timed out)",
        "timeout",
        "medium",
        "An operation exceeded its time limit.",
        "An upstream call is slow or hung, or the timeout is too aggressive.",
        [
            "Check the upstream service's latency and health.",
            "Set a sensible timeout and add bounded retries with backoff.",
        ],
    ),
    _r(
        r"(?:JSONDecodeError|Expecting value|Unexpected token.*JSON|is not valid JSON)",
        "json_parse_error",
        "medium",
        "Failed to parse a response/body as JSON.",
        "The payload was empty, truncated, or actually HTML/text (often an error page).",
        [
            "Log the raw response body and status code before parsing.",
            "Check the content-type and handle non-2xx responses before json().",
        ],
    ),
    _r(
        r"(?:IntegrityError|UNIQUE constraint failed|duplicate key value)",
        "db_constraint",
        "high",
        "A database constraint was violated.",
        "An insert/update conflicts with a unique, foreign-key, or not-null constraint.",
        [
            "Upsert or check for the existing row before inserting.",
            "Ensure required foreign-key rows exist first.",
        ],
    ),
    _r(
        r"(?:OperationalError|could not connect to server|no such table|database is locked)",
        "db_error",
        "high",
        "The database is unreachable or its schema is out of date.",
        "Connectivity is broken or migrations haven't been applied.",
        [
            "Verify the database is up and the connection URL is correct.",
            "Run pending migrations / init so the expected tables exist.",
        ],
    ),
    _r(
        r"(?:RecursionError|maximum recursion depth)",
        "recursion",
        "high",
        "Infinite or excessively deep recursion.",
        "A base case is missing or never reached.",
        [
            "Add/verify the recursion base case.",
            "Consider an iterative rewrite for deep inputs.",
        ],
    ),
    # ── JS / TS / Next.js ──
    _r(
        r"ReferenceError: (\w+) is not defined",
        "undefined_name",
        "high",
        "Referenced an identifier ('{name}') that isn't defined.",
        "A missing import/declaration, or server-only code running on the client.",
        [
            "Import or declare '{name}' before use.",
            "If it's a browser global, guard with `typeof window !== 'undefined'`.",
        ],
    ),
    _r(
        r"Module not found: (?:Error: )?Can't resolve ['\"]([^'\"]+)['\"]",
        "missing_dependency",
        "high",
        "A module import ('{name}') can't be resolved.",
        "The package isn't installed or the relative import path is wrong.",
        [
            "Install the package (npm install {name}) if it's a dependency.",
            "Fix the import path / alias if '{name}' is a local module.",
        ],
    ),
    _r(
        r"(?:Hydration failed|Text content does not match|did not match\. Server)",
        "hydration_mismatch",
        "low",
        "Server-rendered HTML didn't match the client render.",
        "Markup depends on non-deterministic values (Date.now, random, window) during SSR.",
        [
            "Move client-only values into useEffect, or gate them behind a mounted flag.",
            "Keep server and client output identical for the first render.",
        ],
    ),
    _r(
        r"Maximum update depth exceeded",
        "render_loop",
        "high",
        "A React component updated state in an unbounded loop.",
        "setState is called during render or in an effect without correct dependencies.",
        [
            "Don't call setState directly in the render body.",
            "Fix the useEffect dependency array so it doesn't re-run every render.",
        ],
    ),
    _r(
        r"(?:HTTP )?(?:status (?:code )?)?5\d\d|Internal Server Error|Bad Gateway|Service Unavailable",
        "upstream_5xx",
        "high",
        "An upstream/server request returned a 5xx error.",
        "The downstream service errored or is unavailable.",
        [
            "Check the upstream service logs for the underlying exception.",
            "Add retries with backoff and a graceful fallback for 5xx responses.",
        ],
    ),
    _r(
        r"429|Too Many Requests|rate limit",
        "rate_limited",
        "medium",
        "A request was rate-limited (HTTP 429).",
        "Calls exceeded the provider's allowed rate.",
        [
            "Respect the Retry-After header and back off before retrying.",
            "Add client-side throttling / caching to cut request volume.",
        ],
    ),
    _r(
        r"SyntaxError|Unexpected token",
        "syntax_error",
        "high",
        "The code or a parsed payload is syntactically invalid.",
        "A typo in source, or a non-code payload parsed as code/JSON.",
        [
            "Locate the offending line from the stack and fix the syntax.",
            "If parsing data, validate it's the expected format first.",
        ],
    ),
]


_UNKNOWN = Diagnosis(
    category="unknown",
    severity="medium",
    summary="Unrecognised error — manual triage needed.",
    root_cause="No known pattern matched. The message needs a human (or LLM) read.",
    suggested_fix=[
        "Read the stack trace top-down to the first frame in your own code.",
        "Reproduce locally with the same inputs to narrow the cause.",
        "Add logging around the failing call to capture the real state.",
    ],
    likely_files=[],
    confidence="low",
)


def _fill(template: str, name: str | None) -> str:
    """Substitute the captured symbol into a template, with a safe default."""
    return template.replace("{name}", name or "the referenced symbol")


def diagnose_error(
    *,
    title: str = "",
    message: str = "",
    stack_trace: str = "",
) -> Diagnosis:
    """Classify an error into a structured, actionable diagnosis.

    Deterministic and offline: the same input always yields the same result.
    """
    text = "\n".join(part for part in (title, message, stack_trace) if part).strip()
    likely_files = extract_files(stack_trace or message)

    if not text:
        result = Diagnosis(
            category="empty_input",
            severity="low",
            summary="No error text was provided.",
            root_cause="The request contained no title, message, or stack trace to analyse.",
            suggested_fix=["Send the error message and/or stack trace to diagnose."],
            confidence="high",
        )
        return result

    for rule in _RULES:
        match = rule.pattern.search(text)
        if not match:
            continue
        name = match.group(1) if match.groups() else None
        return Diagnosis(
            category=rule.category,
            severity=rule.severity,
            summary=_fill(rule.summary, name),
            root_cause=_fill(rule.root_cause, name),
            suggested_fix=[_fill(step, name) for step in rule.suggested_fix],
            likely_files=likely_files,
            confidence=rule.confidence,
            source="heuristic",
        )

    return Diagnosis(
        category=_UNKNOWN.category,
        severity=_UNKNOWN.severity,
        summary=_UNKNOWN.summary,
        root_cause=_UNKNOWN.root_cause,
        suggested_fix=list(_UNKNOWN.suggested_fix),
        likely_files=likely_files,
        confidence=_UNKNOWN.confidence,
        source="heuristic",
    )

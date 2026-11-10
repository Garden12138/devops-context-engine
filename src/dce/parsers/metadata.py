import hashlib
import json
import re
import shlex
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from typing import Any

import yaml

from dce.common.errors import DceError, ErrorCode

MAX_METADATA_BYTES = 1_000_000


def bounded(text: str) -> None:
    if len(text.encode()) > MAX_METADATA_BYTES:
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Metadata size limit exceeded.")


def safe_path(path: str) -> bool:
    parsed = PurePosixPath(path)
    return (
        not parsed.is_absolute()
        and ".." not in parsed.parts
        and "\\" not in path
        and "\x00" not in path
    )


def yaml_metadata(text: str) -> tuple[dict[str, Any], bool]:
    bounded(text)
    try:
        tokens = list(yaml.scan(text))
        if len(tokens) > 50000:
            raise DceError(ErrorCode.INVALID_PAYLOAD, "YAML node limit exceeded.")
        if any(isinstance(token, (yaml.AliasToken, yaml.AnchorToken)) for token in tokens):
            return {}, True
        data = yaml.safe_load(text)
    except (yaml.YAMLError, RecursionError):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid safe YAML metadata.") from None
    if data is None:
        return {}, False
    if not isinstance(data, dict):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Metadata must be a mapping.")
    return data, False


def image(reference: str) -> dict[str, Any]:
    if (
        not re.fullmatch(r"[\w./:${}-]+(?:@sha256:[a-fA-F0-9]{64})?", reference)
        or "://" in reference
    ):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid OCI image reference.")
    name, sep, digest = reference.partition("@")
    tail = name.rsplit("/", 1)[-1]
    if ":" in tail:
        repository, tag = name.rsplit(":", 1)
    else:
        repository, tag = name, "latest"
    valid_digest = bool(sep and re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest))
    incomplete = bool("$" in reference or not repository or (sep and not valid_digest))
    return {
        "reference": reference,
        "repository": repository,
        "tag": tag,
        "digest": digest if valid_digest else None,
        "mutable_tag": not valid_digest,
        "version_uncertain": not valid_digest or incomplete,
        "incomplete": incomplete,
    }


def compose(text: str) -> dict[str, Any]:
    data, incomplete = yaml_metadata(text)
    services = data.get("services", {})
    if not isinstance(services, dict):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Compose services must be a mapping.")
    result = []
    for name, spec in services.items():
        if not isinstance(name, str) or not isinstance(spec, dict):
            incomplete = True
            continue
        environment = spec.get("environment", {}) or {}
        names: list[str] = []
        if isinstance(environment, dict):
            entries = list(environment)
        elif isinstance(environment, list):
            entries = environment
        else:
            entries = []
            incomplete = True
        for entry in entries:
            if not isinstance(entry, str):
                incomplete = True
                continue
            environment_name = entry.split("=", 1)[0]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,199}", environment_name):
                names.append(environment_name)
            else:
                incomplete = True
        reference = spec.get("image")
        parsed = image(reference) if isinstance(reference, str) else None
        if "extends" in spec or parsed is None or parsed["incomplete"]:
            incomplete = True
        build = spec.get("build")
        context = build.get("context") if isinstance(build, dict) else build
        if context is not None and (not isinstance(context, str) or not safe_path(context)):
            incomplete = True
            context = None
        result.append(
            {
                "name": name,
                "image": parsed,
                "environment_names": sorted(names),
                "build_context": context,
            }
        )
    return {"services": result, "incomplete": incomplete}


def compose_service(text: str, name: str) -> dict[str, Any]:
    """Select before parsing unrelated services. No command, env values, auth or raw YAML."""
    data, unresolved = yaml_metadata(text)
    if unresolved:
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Compose aliases require explicit resolution.")
    services = data.get("services", {})
    if not isinstance(services, dict):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Compose services must be a mapping.")
    if name not in services:
        raise DceError(ErrorCode.NOT_FOUND, "Compose service is not present in this Stack File.")
    spec = services[name]
    if not isinstance(spec, dict):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Unexpected Compose service definition.")
    selected = compose(yaml.safe_dump({"services": {name: spec}}))
    record = {**selected["services"][0], "incomplete": selected["incomplete"]}
    labels = spec.get("labels", {}) or {}
    if isinstance(labels, list):
        labels = dict(
            item.split("=", 1) for item in labels if isinstance(item, str) and "=" in item
        )
    allowed_labels = {
        "com.docker.stack.namespace",
        "com.docker.stack.service.name",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.source",
    }
    record["labels"] = (
        {k: v for k, v in labels.items() if k in allowed_labels and isinstance(v, str)}
        if isinstance(labels, dict)
        else {}
    )
    deploy = spec.get("deploy") or {}
    record["deploy"] = {}
    if isinstance(deploy, dict):
        if deploy.get("mode") in {"replicated", "global", "replicated-job", "global-job"}:
            record["deploy"]["mode"] = deploy["mode"]
        elif "mode" in deploy:
            record["incomplete"] = True
        replicas = deploy.get("replicas")
        if isinstance(replicas, int) and not isinstance(replicas, bool) and replicas >= 0:
            record["deploy"]["replicas"] = replicas
        elif "replicas" in deploy:
            record["incomplete"] = True
    else:
        record["incomplete"] = True
    ports = spec.get("ports", []) or []
    record["ports"] = []
    if not isinstance(ports, list):
        ports = []
        record["incomplete"] = True
    for port in ports:
        safe: dict[str, Any] = {}
        if isinstance(port, (int, str)) and not isinstance(port, bool):
            value, separator, protocol = str(port).partition("/")
            parts = value.rsplit(":", 2)
            if all(re.fullmatch(r"\d+(?:-\d+)?", p) for p in parts[-2:]):
                safe = {"target": parts[-1]}
                if len(parts) > 1:
                    safe["published"] = parts[-2]
                if separator and protocol in {"tcp", "udp", "sctp"}:
                    safe["protocol"] = protocol
                elif separator:
                    record["incomplete"] = True
        elif isinstance(port, dict):
            for field in ("target", "published", "protocol", "mode"):
                if field not in port:
                    continue
                value = port[field]
                valid = (
                    str(value) in {"tcp", "udp", "sctp"}
                    if field == "protocol"
                    else str(value) in {"ingress", "host"}
                    if field == "mode"
                    else isinstance(value, (int, str))
                    and not isinstance(value, bool)
                    and re.fullmatch(r"\d+(?:-\d+)?", str(value)) is not None
                )
                if valid:
                    safe[field] = value
                else:
                    record["incomplete"] = True
        if safe:
            record["ports"].append(safe)
        else:
            record["incomplete"] = True
    return record


def modules(path: str, text: str) -> dict[str, Any]:
    bounded(text)
    name = PurePosixPath(path).name
    found: list[str] = []
    incomplete = False
    try:
        if name == "pom.xml":
            if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
                raise ValueError
            root = ET.fromstring(text)
            found = [
                str(item.text).strip()
                for item in root.findall("./{*}modules/{*}module")
                if item.text
            ]
        elif name in {"settings.gradle", "settings.gradle.kts"}:
            # Ignore comments; accept literal include forms only.
            for line in re.sub(r"/\*.*?\*/", "", text, flags=re.S).splitlines():
                line = line.split("//", 1)[0].strip()
                if re.match(r"include\b", line):
                    quoted = re.findall(r"""["'](:?[\w:./*-]+)["']""", line)
                    found.extend(value.lstrip(":").replace(":", "/") for value in quoted)
                    if not quoted:
                        incomplete = True
        elif name == "go.work":
            block = False
            for line in text.splitlines():
                line = line.split("//", 1)[0].strip()
                if line.startswith("use "):
                    line = line[4:].strip()
                    block = line == "("
                    if block:
                        continue
                elif not block:
                    continue
                if line == ")":
                    block = False
                elif line:
                    found.append(line.strip('"').removeprefix("./"))
        elif name == "go.mod":
            found = ["."] if re.search(r"(?m)^module\s+\S+", text) else []
            incomplete = not bool(found)
        elif name == "package.json":
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError
            workspaces = data.get("workspaces", [])
            if isinstance(workspaces, dict):
                workspaces = workspaces.get("packages", [])
            if not isinstance(workspaces, list) or not all(isinstance(w, str) for w in workspaces):
                raise ValueError
            found = workspaces
        else:
            incomplete = True
    except (ET.ParseError, ValueError, RecursionError):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid module metadata.") from None
    valid = [value for value in found if safe_path(value) and "$" not in value]
    return {"modules": sorted(set(valid)), "incomplete": incomplete or len(valid) != len(found)}


def dockerfile(text: str) -> dict[str, Any]:
    bounded(text)
    bases: list[str] = []
    aliases: set[str] = set()
    copies: list[str] = []
    incomplete = False
    for line in text.replace("\\\n", " ").splitlines():
        try:
            words = shlex.split(line, comments=True)
        except ValueError:
            incomplete = True
            continue
        if not words:
            continue
        directive = words[0].upper()
        if directive == "FROM":
            args = [word for word in words[1:] if not word.startswith("--")]
            if args:
                if args[0] not in aliases:
                    bases.append(args[0])
                if len(args) >= 3 and args[1].upper() == "AS":
                    aliases.add(args[2])
        elif directive in {"COPY", "ADD"} and not any(w.startswith("--from=") for w in words):
            raw = line.split(None, 1)[1]
            if raw.startswith("["):
                try:
                    args = json.loads(raw)
                except ValueError:
                    incomplete = True
                    continue
                if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                    incomplete = True
                    continue
            else:
                args = [word for word in words[1:] if not word.startswith("--")]
            for source in args[:-1]:
                if safe_path(source) and "://" not in source and "$" not in source:
                    copies.append(source)
                else:
                    incomplete = True
    return {
        "base_images": list(dict.fromkeys(bases)),
        "copy_sources": sorted(set(copies)),
        "incomplete": incomplete or any("$" in value for value in bases),
    }


def ci(text: str) -> dict[str, Any]:
    data, incomplete = yaml_metadata(text)
    include = data.get("include", [])
    if isinstance(include, (str, dict)):
        include = [include]
    includes: list[dict[str, Any]] = []
    if not isinstance(include, list):
        include = []
        incomplete = True
    for item in include:
        if isinstance(item, str):
            includes.append({"local": item})
        elif isinstance(item, dict):
            includes.append({k: item[k] for k in ("local", "project", "ref", "file") if k in item})
            if "remote" in item:
                includes[-1]["remote_ref"] = hashlib.sha256(
                    str(item["remote"]).encode()
                ).hexdigest()
        incomplete = True  # References explicit; recursive resolution belongs to P1.
    jobs = []
    reserved = {
        "include",
        "stages",
        "variables",
        "default",
        "workflow",
        "image",
        "services",
        "cache",
    }
    for name, spec in data.items():
        if not isinstance(name, str) or name in reserved or name.startswith("."):
            continue
        if not isinstance(spec, dict):
            continue
        scripts = spec.get("script", [])
        if isinstance(scripts, str):
            scripts = [scripts]
        if not isinstance(scripts, list):
            scripts = []
            incomplete = True
        images, paths, dockerfiles = set(), set(), set()
        for script in scripts:
            if not isinstance(script, str):
                incomplete = True
                continue
            # Bounded extraction of literal arguments only; scripts never leave parser.
            if re.search(r"\bdocker\s+(?:buildx\s+)?build\b", script):
                images.update(re.findall(r"(?:--tag[= ]|-t\s+)([\w./:@${}-]+)", script))
                dockerfiles.update(re.findall(r"(?:--file[= ]|-f\s+)([\w./-]+)", script))
            for group in re.findall(r"(?:-pl|--projects)\s+([\w./,-]+)", script):
                paths.update(group.split(","))
            paths.update(re.findall(r"(?<!\w):([\w-]+):(?:build|assemble|bootJar)\b", script))
        literal_images = sorted(value for value in images if "$" not in value)
        incomplete |= len(literal_images) != len(images) or "extends" in spec
        jobs.append(
            {
                "name": name,
                "stage": str(spec.get("stage", "test")),
                "images": literal_images,
                "module_paths": sorted(value for value in paths if safe_path(value)),
                "dockerfiles": sorted(value for value in dockerfiles if safe_path(value)),
            }
        )
    return {"includes": includes, "jobs": jobs, "incomplete": incomplete}

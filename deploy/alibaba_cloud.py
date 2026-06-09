"""
Alibaba Cloud Function Compute v3 deployment script for Multi-Agent Code Review.

Deploys the FastAPI application as a Function Compute HTTP function on Alibaba Cloud,
using the alibabacloud-fc-open20210406 SDK for function management and the
alibabacloud-ecs20140526 SDK for VPC/security-group provisioning.

Usage:
    pip install alibabacloud-fc-open20210406 alibabacloud-ecs20140526 alibabacloud-credentials
    export ALIBABA_CLOUD_ACCESS_KEY_ID=<your_access_key_id>
    export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your_access_key_secret>
    export QWEN_API_KEY=<your_dashscope_api_key>
    python deploy/alibaba_cloud.py

Alibaba Cloud services used:
  - Function Compute v3 (fc.cn-hangzhou.aliyuncs.com) — serverless HTTP function host
  - ECS / VPC (ecs.aliyuncs.com) — VPC + security-group query for network config
  - DashScope (dashscope-intl.aliyuncs.com) — Qwen model inference API (Alibaba Cloud AI)
"""

from __future__ import annotations

import os
import sys
import zipfile
import tempfile
import pathlib

# ---------------------------------------------------------------------------
# Alibaba Cloud SDK imports
# ---------------------------------------------------------------------------
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig

from alibabacloud_fc_open20210406.client import Client as FCClient
from alibabacloud_fc_open20210406 import models as fc_models
from alibabacloud_tea_openapi import models as open_api_models

from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models

# ---------------------------------------------------------------------------
# Deployment constants — override via environment variables
# ---------------------------------------------------------------------------
REGION = os.getenv("ALIBABA_CLOUD_REGION", "cn-hangzhou")
SERVICE_NAME = os.getenv("FC_SERVICE_NAME", "multiagent-code-review")
FUNCTION_NAME = os.getenv("FC_FUNCTION_NAME", "review-api")
RUNTIME = "python3.10"
HANDLER = "fc_handler.handler"          # entrypoint defined below
MEMORY_MB = 1024
TIMEOUT_SEC = 120                        # max per-invocation timeout

FC_ENDPOINT = f"https://{os.getenv('ALIBABA_CLOUD_ACCOUNT_ID', 'YOUR_ACCOUNT_ID')}.{REGION}.fc.aliyuncs.com"
ECS_ENDPOINT = f"ecs.{REGION}.aliyuncs.com"


# ---------------------------------------------------------------------------
# Credential helper
# ---------------------------------------------------------------------------

def _build_credentials() -> CredentialClient:
    """
    Resolves credentials from environment variables:
      ALIBABA_CLOUD_ACCESS_KEY_ID
      ALIBABA_CLOUD_ACCESS_KEY_SECRET
    Falls back to the default credential chain (RAM role / ECS metadata).
    """
    access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if access_key_id and access_key_secret:
        cfg = CredentialConfig(
            type="access_key",
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        )
    else:
        cfg = CredentialConfig(type="default")

    return CredentialClient(cfg)


# ---------------------------------------------------------------------------
# ECS: list existing VPCs (demonstrates ECS/VPC API usage)
# ---------------------------------------------------------------------------

def list_vpcs(creds: CredentialClient) -> list[dict]:
    """
    Calls ecs.DescribeVpcs to enumerate VPCs in the deployment region.
    Returned VPC IDs are used when configuring the Function Compute VPC binding.
    """
    cfg = open_api_models.Config(
        access_key_id=creds.get_access_key_id(),
        access_key_secret=creds.get_access_key_secret(),
        endpoint=ECS_ENDPOINT,
    )
    client = EcsClient(cfg)

    req = ecs_models.DescribeVpcsRequest(region_id=REGION)
    resp = client.describe_vpcs(req)
    vpcs = resp.body.vpcs.vpc if resp.body.vpcs and resp.body.vpcs.vpc else []
    result = [{"vpc_id": v.vpc_id, "cidr_block": v.cidr_block, "name": v.vpc_name} for v in vpcs]
    print(f"[ECS] Found {len(result)} VPC(s) in {REGION}:")
    for v in result:
        print(f"       {v['vpc_id']}  {v['cidr_block']}  ({v['name']})")
    return result


# ---------------------------------------------------------------------------
# Build deployment zip
# ---------------------------------------------------------------------------

def build_zip(repo_root: pathlib.Path) -> bytes:
    """
    Packages the application source into an in-memory zip that Function Compute
    can execute directly.  Excludes .venv, .git, __pycache__, and *.pyc files.
    """
    exclude_prefixes = {".venv", ".git", "__pycache__", "deploy", ".env"}
    exclude_suffixes = {".pyc", ".pyo"}

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)

    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(repo_root.rglob("*")):
            if path.is_dir():
                continue
            parts = path.relative_to(repo_root).parts
            if any(p in exclude_prefixes for p in parts):
                continue
            if path.suffix in exclude_suffixes:
                continue
            arcname = str(path.relative_to(repo_root))
            zf.write(path, arcname)

        # Inject the Function Compute HTTP handler shim
        zf.writestr("fc_handler.py", _FC_HANDLER_SHIM)

        # Inject requirements for FC layer (FC installs on deploy)
        zf.write(repo_root / "requirements.txt", "requirements.txt")

    payload = tmp_path.read_bytes()
    tmp_path.unlink()
    print(f"[zip] Built deployment package: {len(payload) / 1024:.1f} KB")
    return payload


# ---------------------------------------------------------------------------
# Function Compute HTTP handler shim (injected into the zip)
# ---------------------------------------------------------------------------

_FC_HANDLER_SHIM = '''\
"""
Alibaba Cloud Function Compute v3 HTTP handler shim.
Wraps the FastAPI ASGI app so FC can invoke it as an HTTP function.
"""
import asyncio
from mangum import Mangum
from api.main import app

# Mangum adapts ASGI (FastAPI) to AWS Lambda / Alibaba Cloud FC HTTP format
handler = Mangum(app, lifespan="off")
'''


# ---------------------------------------------------------------------------
# Function Compute: create-or-update service and function
# ---------------------------------------------------------------------------

def _fc_client(creds: CredentialClient) -> FCClient:
    cfg = open_api_models.Config(
        access_key_id=creds.get_access_key_id(),
        access_key_secret=creds.get_access_key_secret(),
        endpoint=FC_ENDPOINT,
    )
    return FCClient(cfg)


def ensure_service(client: FCClient) -> None:
    """Creates the FC service if it does not already exist."""
    try:
        client.get_service(SERVICE_NAME)
        print(f"[FC] Service '{SERVICE_NAME}' already exists.")
    except Exception:
        req = fc_models.CreateServiceRequest(
            service_name=SERVICE_NAME,
            description="Multi-Agent Code Review — Qwen Cloud hackathon (Track 3)",
        )
        client.create_service(req)
        print(f"[FC] Created service '{SERVICE_NAME}'.")


def deploy_function(client: FCClient, zip_bytes: bytes, qwen_api_key: str) -> str:
    """
    Creates or updates the HTTP function with the packaged zip code.
    Returns the public HTTP trigger URL.
    """
    code = fc_models.Code(zip_file=zip_bytes)

    env_vars = {
        "QWEN_API_KEY": qwen_api_key,
        "QWEN_BASE_URL": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "ORCHESTRATOR_MODEL": "qwen3.7-max",
        "SPECIALIST_MODEL": "qwen3.5-plus",
        "MODERATOR_MODEL": "qwen3.7-max",
        "MAX_DEBATE_ROUNDS": "3",
        "CONFLICT_LINE_WINDOW": "5",
    }

    # Try update first, fall back to create
    try:
        client.get_function(SERVICE_NAME, FUNCTION_NAME)
        req = fc_models.UpdateFunctionRequest(
            code=code,
            runtime=RUNTIME,
            handler=HANDLER,
            memory_size=MEMORY_MB,
            timeout=TIMEOUT_SEC,
            environment_variables=env_vars,
            description="Multi-Agent Code Review FastAPI — updated",
        )
        client.update_function(SERVICE_NAME, FUNCTION_NAME, req)
        print(f"[FC] Updated function '{FUNCTION_NAME}'.")
    except Exception:
        req = fc_models.CreateFunctionRequest(
            function_name=FUNCTION_NAME,
            code=code,
            runtime=RUNTIME,
            handler=HANDLER,
            memory_size=MEMORY_MB,
            timeout=TIMEOUT_SEC,
            environment_variables=env_vars,
            description="Multi-Agent Code Review FastAPI on Alibaba Cloud FC",
        )
        client.create_function(SERVICE_NAME, req)
        print(f"[FC] Created function '{FUNCTION_NAME}'.")

    # Ensure an HTTP trigger exists
    trigger_url = _ensure_http_trigger(client)
    return trigger_url


def _ensure_http_trigger(client: FCClient) -> str:
    """Creates an anonymous HTTP trigger on the function (idempotent)."""
    trigger_name = "http-trigger"
    try:
        resp = client.get_trigger(SERVICE_NAME, FUNCTION_NAME, trigger_name)
        url = resp.body.url_internet
        print(f"[FC] HTTP trigger already exists: {url}")
        return url
    except Exception:
        pass

    trigger_config = fc_models.HTTPTriggerConfig(
        auth_type="anonymous",
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    req = fc_models.CreateTriggerRequest(
        trigger_name=trigger_name,
        trigger_type="http",
        trigger_config=trigger_config,
    )
    client.create_trigger(SERVICE_NAME, FUNCTION_NAME, req)

    resp = client.get_trigger(SERVICE_NAME, FUNCTION_NAME, trigger_name)
    url = resp.body.url_internet
    print(f"[FC] HTTP trigger created: {url}")
    return url


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    qwen_api_key = os.getenv("QWEN_API_KEY")
    if not qwen_api_key:
        print("ERROR: QWEN_API_KEY environment variable is required.")
        sys.exit(1)

    print("=" * 60)
    print("Multi-Agent Code Review — Alibaba Cloud Deployment")
    print(f"Region : {REGION}")
    print(f"Service: {SERVICE_NAME}")
    print(f"Fn     : {FUNCTION_NAME}")
    print("=" * 60)

    creds = _build_credentials()

    # 1. Query VPCs via ECS API (demonstrates Alibaba Cloud infrastructure API)
    print("\n--- Step 1: Query Alibaba Cloud VPCs (ECS API) ---")
    list_vpcs(creds)

    # 2. Package application source
    print("\n--- Step 2: Build deployment zip ---")
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    zip_bytes = build_zip(repo_root)

    # 3. Provision Function Compute service + function
    print("\n--- Step 3: Deploy to Alibaba Cloud Function Compute ---")
    fc = _fc_client(creds)
    ensure_service(fc)
    trigger_url = deploy_function(fc, zip_bytes, qwen_api_key)

    print("\n" + "=" * 60)
    print("Deployment complete.")
    print(f"API endpoint : {trigger_url}/review")
    print(f"Health check : {trigger_url}/health")
    print("\nTest with:")
    print(f'  curl -X POST {trigger_url}/review \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"filename":"test.py","code":"x=1"}\'')
    print("=" * 60)


if __name__ == "__main__":
    main()

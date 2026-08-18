"""
Cleanup script: deletes all AWS resources created by this module's deployment.

Usage:
    python cleanup.py --runtime-name sequential-chain

What it deletes:
  1. AgentCore Runtime endpoint
  2. AgentCore Runtime
  3. IAM execution role and inline policies
  4. ECR repository and all images
  5. CodeBuild project (used by agentcore deploy for the container build)
  6. CloudFormation stack (AgentCore-* created by agentcore deploy)

Run this BEFORE `agentcore remove all -y` if you want boto3-driven cleanup,
OR run ONLY `agentcore remove all -y` + `agentcore deploy` for CDK-driven cleanup.
"""

import argparse
import boto3
import json
import sys
import time

REGION = "us-east-1"

agentcore = boto3.client("bedrock-agentcore-control", region_name=REGION)
iam       = boto3.client("iam", region_name=REGION)
ecr       = boto3.client("ecr", region_name=REGION)
cfn       = boto3.client("cloudformation", region_name=REGION)
cb        = boto3.client("codebuild", region_name=REGION)


def find_runtime(name: str):
    """Find runtime ARN and ID by name."""
    resp = agentcore.list_agent_runtimes()
    for rt in resp.get("agentRuntimes", []):
        if rt["agentRuntimeName"] == name:
            return rt["agentRuntimeArn"], rt["agentRuntimeId"]
    return None, None


def delete_runtime_endpoint(runtime_id: str):
    """Delete the DEFAULT endpoint for a runtime."""
    try:
        resp = agentcore.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in resp.get("runtimeEndpoints", []):
            ep_id = ep["endpointId"]
            print(f"  Deleting endpoint {ep_id}...")
            agentcore.delete_agent_runtime_endpoint(
                agentRuntimeId=runtime_id,
                endpointName=ep_id,
            )
            # Wait until deleted
            for _ in range(30):
                try:
                    agentcore.get_agent_runtime_endpoint(
                        agentRuntimeId=runtime_id, endpointName=ep_id
                    )
                    time.sleep(5)  # nosemgrep: arbitrary-sleep: polling for resource deletion
                except agentcore.exceptions.ResourceNotFoundException:
                    print(f"  Endpoint {ep_id} deleted.")
                    break
    except Exception as e:
        print(f"  Warning: could not delete endpoints: {e}")


def delete_runtime(runtime_arn: str, runtime_id: str):
    print(f"  Deleting runtime {runtime_id}...")
    agentcore.delete_agent_runtime(agentRuntimeId=runtime_id)
    for _ in range(30):
        try:
            agentcore.get_agent_runtime(agentRuntimeId=runtime_id)
            time.sleep(5)  # nosemgrep: arbitrary-sleep: polling for resource deletion
        except agentcore.exceptions.ResourceNotFoundException:
            print("  Runtime deleted.")
            return
    print("  Warning: timed out waiting for runtime deletion.")


def delete_iam_role(role_prefix: str):
    """Delete IAM roles whose name starts with role_prefix."""
    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            if role["RoleName"].startswith(role_prefix):
                name = role["RoleName"]
                print(f"  Deleting IAM role {name}...")
                # Detach managed policies
                for p in iam.list_attached_role_policies(RoleName=name)["AttachedPolicies"]:
                    iam.detach_role_policy(RoleName=name, PolicyArn=p["PolicyArn"])
                # Delete inline policies
                for pname in iam.list_role_policies(RoleName=name)["PolicyNames"]:
                    iam.delete_role_policy(RoleName=name, PolicyName=pname)
                iam.delete_role(RoleName=name)
                print(f"  IAM role {name} deleted.")


def delete_ecr_repo(repo_prefix: str):
    """Delete ECR repos whose name starts with repo_prefix."""
    try:
        repos = ecr.describe_repositories()["repositories"]
        for repo in repos:
            if repo["repositoryName"].startswith(repo_prefix):
                name = repo["repositoryName"]
                print(f"  Deleting ECR repository {name}...")
                ecr.delete_repository(repositoryName=name, force=True)
                print(f"  ECR repository {name} deleted.")
    except Exception as e:
        print(f"  Warning: ECR cleanup: {e}")


def delete_cfn_stack(stack_prefix: str):
    """Delete CloudFormation stack whose name starts with stack_prefix."""
    try:
        stacks = cfn.describe_stacks()["Stacks"]
        for stack in stacks:
            if stack["StackName"].startswith(stack_prefix):
                name = stack["StackName"]
                print(f"  Deleting CloudFormation stack {name}...")
                cfn.delete_stack(StackName=name)
                waiter = cfn.get_waiter("stack_delete_complete")
                waiter.wait(StackName=name)
                print(f"  Stack {name} deleted.")
    except Exception as e:
        print(f"  Warning: CloudFormation cleanup: {e}")


def delete_codebuild_project(project_prefix: str):
    """Delete CodeBuild project whose name starts with project_prefix."""
    try:
        projects = cb.list_projects()["projects"]
        for p in projects:
            if p.startswith(project_prefix):
                print(f"  Deleting CodeBuild project {p}...")
                cb.delete_project(name=p)
                print(f"  CodeBuild project {p} deleted.")
    except Exception as e:
        print(f"  Warning: CodeBuild cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(description="Delete AgentCore Runtime and related resources.")
    parser.add_argument("--runtime-name", required=True, help="AgentCore Runtime name to delete")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()

    name = args.runtime_name
    print(f"\nCleanup for runtime: {name}")
    print("=" * 60)

    # 1. Find runtime
    runtime_arn, runtime_id = find_runtime(name)
    if not runtime_arn:
        print(f"Runtime '{name}' not found. Already deleted?")
    else:
        print(f"Found: {runtime_arn}")
        if not args.dry_run:
            delete_runtime_endpoint(runtime_id)
            delete_runtime(runtime_arn, runtime_id)
        else:
            print("  [DRY RUN] Would delete endpoint and runtime")

    # 2. IAM roles
    print("\nCleaning IAM roles (prefix: AmazonBedrockAgentCoreSDK)...")
    if not args.dry_run:
        delete_iam_role("AmazonBedrockAgentCoreSDK")
    else:
        print("  [DRY RUN] Would delete AmazonBedrockAgentCoreSDK* roles")

    # 3. ECR
    print("\nCleaning ECR repositories (prefix: bedrock-agentcore)...")
    if not args.dry_run:
        delete_ecr_repo("bedrock-agentcore")
    else:
        print("  [DRY RUN] Would delete bedrock-agentcore-* ECR repos")

    # 4. CodeBuild
    print("\nCleaning CodeBuild projects (prefix: bedrock-agentcore)...")
    if not args.dry_run:
        delete_codebuild_project("bedrock-agentcore")
    else:
        print("  [DRY RUN] Would delete bedrock-agentcore-* CodeBuild projects")

    # 5. CloudFormation (created by agentcore deploy via CDK)
    print(f"\nCleaning CloudFormation stack (prefix: AgentCore-{name})...")
    if not args.dry_run:
        delete_cfn_stack(f"AgentCore-{name}")
    else:
        print(f"  [DRY RUN] Would delete AgentCore-{name}* CFN stacks")

    print("\nCleanup complete.")
    print("\nVerify nothing remains:")
    print("  aws bedrock-agentcore-control list-agent-runtimes --region us-east-1")
    print("  aws cloudformation describe-stacks --region us-east-1 | grep AgentCore")


if __name__ == "__main__":
    main()

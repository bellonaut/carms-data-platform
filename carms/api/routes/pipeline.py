from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from carms.core.config import Settings

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
settings = Settings()

REPOSITORIES_QUERY = """
query Repositories {
  repositoriesOrError {
    __typename
    ... on RepositoryConnection {
      nodes {
        name
        location {
          name
        }
        jobs {
          name
        }
      }
    }
    ... on PythonError {
      message
      stack
    }
  }
}
"""

LAUNCH_RUN_MUTATION = """
mutation LaunchRun($executionParams: ExecutionParams!) {
  launchPipelineExecution(executionParams: $executionParams) {
    __typename
    ... on LaunchRunSuccess {
      run {
        runId
      }
    }
    ... on InvalidStepError {
      invalidStepKey
    }
    ... on PipelineNotFoundError {
      message
    }
    ... on PythonError {
      message
      stack
    }
  }
}
"""


class PipelineRunResponse(BaseModel):
    status: Literal["success", "error"]
    detail: str
    run_id: str | None = None


async def _graphql_request(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.dagster_graphql_url,
            json={"query": query, "variables": variables or {}},
        )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise HTTPException(status_code=502, detail=f"Dagster GraphQL errors: {payload['errors']}")
    return payload.get("data", {})


def _resolve_job_selector(data: dict[str, Any], job_name: str) -> dict[str, str]:
    repositories = data.get("repositoriesOrError", {})
    if repositories.get("__typename") != "RepositoryConnection":
        raise HTTPException(status_code=502, detail="Dagster repositories query failed")

    for node in repositories.get("nodes", []):
        jobs = node.get("jobs", [])
        if any(job.get("name") == job_name for job in jobs):
            return {
                "repositoryLocationName": node["location"]["name"],
                "repositoryName": node["name"],
                "pipelineName": job_name,
            }

    raise HTTPException(status_code=404, detail=f"Dagster job not found: {job_name}")


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline() -> PipelineRunResponse:
    """Trigger Dagster asset job execution through Dagster GraphQL API."""
    try:
        repos_data = await _graphql_request(REPOSITORIES_QUERY)
        selector = _resolve_job_selector(repos_data, "carms_job")

        launch_variables = {
            "executionParams": {
                "selector": selector,
                "runConfigData": {},
                "mode": "default",
            }
        }
        launch_data = await _graphql_request(LAUNCH_RUN_MUTATION, launch_variables)
        launch = launch_data.get("launchPipelineExecution", {})
        launch_type = launch.get("__typename")

        if launch_type == "LaunchRunSuccess":
            run_id = launch.get("run", {}).get("runId")
            return PipelineRunResponse(
                status="success",
                detail="Dagster run successfully launched via GraphQL",
                run_id=run_id,
            )

        return PipelineRunResponse(
            status="error",
            detail=f"Dagster launch failed: {launch_type} {launch}",
            run_id=None,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Unable to contact Dagster GraphQL: {exc}"
        ) from exc

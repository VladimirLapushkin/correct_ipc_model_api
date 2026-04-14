
import json
import requests
from dotenv import dotenv_values
from loguru import logger

# Загружаем .env
secrets = dotenv_values(".env")

GITHUB_TOKEN = secrets.get("GITHUB_TOKEN")
GITHUB_REPO = secrets.get("GITHUB_REPO")  # формат: owner/repo
WORKFLOW_FILENAME = secrets.get("GITHUB_WORKFLOW_DEPLOY_FILE", "ci-cd.yml")
WORKFLOW_REF = secrets.get("GITHUB_WORKFLOW_REF", "main")
WORKFLOW_ENV = secrets.get("GITHUB_WORKFLOW_ENV", "dev")

if not GITHUB_TOKEN or not GITHUB_REPO:
    raise ValueError("GITHUB_TOKEN и GITHUB_REPO должны быть определены в .env")

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILENAME}/dispatches"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

def trigger_workflow(env: str) -> None:
    """
    Trigger 'Deploy correct-ipc' workflow via workflow_dispatch.
    """
    payload = {
        "ref": WORKFLOW_REF,
        "inputs": {
            "env": env,
        },
    }

    logger.info(f"Triggering workflow {WORKFLOW_FILENAME} on ref={WORKFLOW_REF}, env={env}")
    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)

    if response.status_code == 204:
        logger.success("Workflow dispatched successfully.")
    elif response.status_code == 201:
        # иногда API может вернуть 201 при создании
        logger.success("Workflow dispatched (201 Created).")
    else:
        logger.error(f"Failed to dispatch workflow: {response.status_code} {response.text}")
        response.raise_for_status()

def main() -> None:
    env = WORKFLOW_ENV
    trigger_workflow(env)

if __name__ == "__main__":
    main()

import os
from google.cloud.devtools import cloudbuild_v1
from google.cloud import artifactregistry_v1
from google.cloud import run_v2

# 🔹 Config
PROJECT_ID = "fluted-century-471609-u9"       # Replace with your GCP project ID
SERVICE_NAME = "ai-chat-service"
REPO_ID = "ai-chat-repo"
SOURCE_DIR = "./backend"     # Path to your backend code
REGIONS = ["asia-south1", "us-central1"]  # India + US

# Artifact Registry image (global naming, used across regions)
IMAGE_NAME = f"{REGIONS[0]}-docker.pkg.dev/{PROJECT_ID}/{REPO_ID}/{SERVICE_NAME}"

# 1. Create Artifact Registry Repo (in first region only)
def create_repo(region):
    client = artifactregistry_v1.ArtifactRegistryClient()
    parent = f"projects/{PROJECT_ID}/locations/{region}"
    repo_name = f"{parent}/repositories/{REPO_ID}"

    try:
        client.get_repository(name=repo_name)
        print(f"⚠️ Repo already exists in {region}: {REPO_ID}")
    except:
        repo = artifactregistry_v1.Repository(
            name=repo_name,
            format=artifactregistry_v1.Repository.Format.DOCKER,
        )
        op = client.create_repository(
            parent=parent, repository_id=REPO_ID, repository=repo
        )
        op.result()
        print(f"✅ Created repo in {region}: {REPO_ID}")

# 2. Build & Push Docker Image (once, to Artifact Registry)
def build_and_push():
    client = cloudbuild_v1.services.cloud_build.CloudBuildClient()

    build = cloudbuild_v1.Build(
        steps=[
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", IMAGE_NAME, "."],
                "dir_": SOURCE_DIR,
            },
            {
                "name": "gcr.io/cloud-builders/docker",
                "args": ["push", IMAGE_NAME],
                "dir_": SOURCE_DIR,
            },
        ],
        images=[IMAGE_NAME],
    )

    op = client.create_build(project_id=PROJECT_ID, build=build)
    op.result()
    print(f"✅ Built & pushed image: {IMAGE_NAME}")
    return IMAGE_NAME

# 3. Deploy to Cloud Run (for each region)
def deploy_cloud_run(image_url, region):
    client = run_v2.ServicesClient()
    parent = f"projects/{PROJECT_ID}/locations/{region}"

    service = run_v2.Service()
    service.name = f"{parent}/services/{SERVICE_NAME}"
    container = run_v2.Container()
    container.image = image_url
    service.template.containers = [container]

    try:
        existing = client.get_service(name=service.name)
        print(f"⚠️ Updating existing service in {region}...")
        op = client.update_service(service=service)
    except:
        print(f"🚀 Creating new service in {region}...")
        op = client.create_service(parent=parent, service=service)

    result = op.result()
    url = result.uri
    print(f"✅ Service deployed in {region}: {url}")
    return url


if __name__ == "__main__":
    # Step 1: Create repo (only in asia-south1)
    create_repo(REGIONS[0])

    # Step 2: Build & push image
    image_url = build_and_push()

    # Step 3: Deploy service in each region
    urls = []
    for region in REGIONS:
        url = deploy_cloud_run(image_url, region)
        urls.append(url)

    print("\n🎯 Deployment complete!")
    for region, url in zip(REGIONS, urls):
        print(f"   {region}: {url}")

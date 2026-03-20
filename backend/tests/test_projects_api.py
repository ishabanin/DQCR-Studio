from fastapi.testclient import TestClient


def test_projects_list_and_create(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/projects")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert "demo" in ids

    create_response = api_client.post(
        "/api/v1/projects",
        json={
            "project_id": "newproj",
            "name": "New Project",
            "description": "from test",
            "template": "flx",
            "contexts": ["default", "dev"],
            "properties": {"owner": "qa"},
            "model": {
                "name": "SampleModel",
                "first_folder": "01_stage",
                "attributes": [{"name": "id", "domain_type": "number", "is_key": True}],
            },
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["id"] == "newproj"

    contexts_response = api_client.get("/api/v1/projects/newproj/contexts")
    assert contexts_response.status_code == 200
    context_ids = [item["id"] for item in contexts_response.json()]
    assert "default" in context_ids
    assert "dev" in context_ids


def test_validate_api_and_history(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/projects/demo/validate",
        json={"model_id": "SampleModel", "categories": ["general", "sql", "descriptions"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project"] == "demo"
    assert body["model"] == "SampleModel"
    assert "summary" in body
    assert isinstance(body["rules"], list)
    assert len(body["rules"]) > 0

    history_response = api_client.get("/api/v1/projects/demo/validate/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 1
    assert history[0]["run_id"] == body["run_id"]


def test_build_api_history_and_files(api_client: TestClient) -> None:
    build_response = api_client.post(
        "/api/v1/projects/demo/build",
        json={
            "model_id": "SampleModel",
            "engine": "dqcr",
            "context": "default",
            "dry_run": False,
        },
    )
    assert build_response.status_code == 200
    build = build_response.json()
    build_id = build["build_id"]
    assert build["files_count"] >= 1

    history_response = api_client.get("/api/v1/projects/demo/build/history")
    assert history_response.status_code == 200
    assert history_response.json()[0]["build_id"] == build_id

    files_response = api_client.get(f"/api/v1/projects/demo/build/{build_id}/files")
    assert files_response.status_code == 200
    files_payload = files_response.json()
    assert files_payload["build_id"] == build_id
    assert len(files_payload["files"]) >= 1

    download_response = api_client.get(f"/api/v1/projects/demo/build/{build_id}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("application/zip")


def test_files_create_folder_and_content(api_client: TestClient) -> None:
    folder_response = api_client.post(
        "/api/v1/projects/demo/files/folder",
        json={"path": "model/SampleModel/workflow/02_new"},
    )
    assert folder_response.status_code == 200
    assert folder_response.json()["path"] == "model/SampleModel/workflow/02_new"

    file_response = api_client.put(
        "/api/v1/projects/demo/files/content",
        json={
            "path": "model/SampleModel/workflow/02_new/001_extra.sql",
            "content": "select 1\n",
        },
    )
    assert file_response.status_code == 200

    read_response = api_client.get(
        "/api/v1/projects/demo/files/content",
        params={"path": "model/SampleModel/workflow/02_new/001_extra.sql"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["content"] == "select 1\n"

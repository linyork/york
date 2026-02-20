
import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.structure.detector import detect_project_structure

@pytest.mark.asyncio
async def test_detect_project_structure_disclosure_vulnerability():
    # Setup mock config
    with patch("src.config.config") as mock_config:
        projects_root = Path("/tmp/york_projects")
        projects_root.mkdir(parents=True, exist_ok=True)
        mock_config.projects_root = str(projects_root)

        # Create a secret file outside projects root
        secret_file = Path("/tmp/york_secret.txt")
        secret_file.write_text("secret info")

        try:
            # The fixed code should reject paths outside projects_root
            result = await detect_project_structure(str(secret_file), "test_project")

            assert "錯誤" in result
            assert "不位於允許的目錄內" in result

        finally:
            if secret_file.exists():
                secret_file.unlink()
            if projects_root.exists():
                import shutil
                shutil.rmtree(projects_root)

@pytest.mark.asyncio
async def test_detect_project_structure_path_traversal():
    # Setup mock config
    with patch("src.config.config") as mock_config:
        projects_root = Path("/tmp/york_projects")
        projects_root.mkdir(parents=True, exist_ok=True)
        mock_config.projects_root = str(projects_root)

        # Path traversal attempt
        traversal_path = "../../../etc/passwd"

        result = await detect_project_structure(traversal_path, "test_project")

        # The fixed code should reject traversal
        assert "錯誤" in result
        assert "不位於允許的目錄內" in result

@pytest.mark.asyncio
async def test_detect_project_structure_valid_path():
    # Setup mock config
    with patch("src.config.config") as mock_config:
        projects_root = Path("/tmp/york_projects")
        projects_root.mkdir(parents=True, exist_ok=True)
        mock_config.projects_root = str(projects_root)

        # Create a valid project directory
        project_name = "valid_project"
        project_path = projects_root / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "package.json").write_text("{}")

        try:
            # Test with project name (should be found under projects_root)
            result = await detect_project_structure(project_name, project_name)
            assert "錯誤" not in result
            assert "project: valid_project" in result

            # Test with relative path
            result = await detect_project_structure(f"./{project_name}", project_name)
            assert "錯誤" not in result

        finally:
            import shutil
            shutil.rmtree(projects_root)

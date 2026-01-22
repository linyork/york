"""
專案結構自動偵測器
掃描目錄特徵並生成 project.structure.yml 建議
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from src.utils.logger import Logger

class FrameworkDetector:
    """框架偵測器"""
    
    # 框架特徵定義
    FRAMEWORKS = {
        "Laravel": {
            "checks": ["artisan", "composer.json"],  # 必須存在的檔案
            "dirs": ["app/Http/Controllers", "app/Models", "routes", "resources/views"] 
        },
        "FuelPHP": {
            "checks": ["oil", "fuel/app/bootstrap.php"],
            "dirs": ["fuel/app/classes/controller", "fuel/app/classes/model", "fuel/app/views"]
        },
        "NodeJS": {
            "checks": ["package.json"],
            "dirs": ["src", "node_modules"]
        },
        "Python": {
            "checks": ["requirements.txt", "pyproject.toml", "setup.py"],
            "dirs": ["venv", ".venv"]
        }
    }

    @staticmethod
    def detect(project_path: str) -> Optional[str]:
        """偵測專案使用的框架"""
        path = Path(project_path)
        if not path.exists():
            return None
            
        scores = {}
        
        for name, rules in FrameworkDetector.FRAMEWORKS.items():
            score = 0
            # 檢查關鍵檔案
            for check in rules["checks"]:
                if (path / check).exists():
                    score += 10
            
            # 檢查關鍵目錄
            for directory in rules["dirs"]:
                if (path / directory).exists():
                    score += 5
            
            if score > 0:
                scores[name] = score
        
        if not scores:
            return None
            
        # 回傳分數最高的框架
        return max(scores, key=scores.get)

    @staticmethod
    def generate_suggestion(project_name: str, framework: str, project_path: str) -> str:
        """生成建議的 YAML 配置"""
        
        # 基礎結構
        structure = {
            "project": project_name,
            "framework": framework,
            "directories": [],
            "ingore_patterns": [
                "node_modules/**",
                "vendor/**",
                ".git/**",
                "storage/**",
                "**/__pycache__/**"
            ]
        }
        
        # 根據框架加入建議目錄
        if framework == "Laravel":
            structure["directories"] = [
                {"path": "app/Http/Controllers", "description": "HTTP Controllers", "tags": ["controller", "logic"]},
                {"path": "app/Models", "description": "Eloquent Models", "tags": ["model", "database"]},
                {"path": "app/Services", "description": "Business Logic Services", "tags": ["service", "logic"]},
                {"path": "routes", "description": "Route Definitions", "tags": ["route", "config"]},
                {"path": "config", "description": "Configuration Files", "tags": ["config"]}
            ]
        elif framework == "FuelPHP":
            structure["directories"] = [
                {"path": "fuel/app/classes/controller", "description": "Controllers", "tags": ["controller"]},
                {"path": "fuel/app/classes/model", "description": "Models", "tags": ["model"]},
                {"path": "fuel/app/classes/service", "description": "Services", "tags": ["service"]},
                {"path": "fuel/app/config", "description": "Config", "tags": ["config"]}
            ]
        elif framework == "NodeJS":
             structure["directories"] = [
                {"path": "src", "description": "Source Code", "tags": ["source"]}
            ]
        elif framework == "Python":
             structure["directories"] = [
                {"path": "src", "description": "Source Code", "tags": ["source"]},
                {"path": "tests", "description": "Tests", "tags": ["test"]}
            ]
            
        # 轉換為 YAML 字串
        return yaml.dump(structure, allow_unicode=True, sort_keys=False)

async def detect_project_structure(project_path: str, project_name: str) -> str:
    """
    執行結構偵測並回傳建議
    """
    Logger.info("Structure", f"開始偵測專案結構: {project_path}")
    
    # 路徑修正邏輯 (Host -> Container)
    # 若在 Docker 內執行，外部傳入的路徑可能無法直接存取
    # 這裡假設使用者傳入的是 Docker 內的路徑，或者是標準專案路徑
    
    # 簡單的路徑檢查
    target_path = Path(project_path)
    
    # 如果路徑不存在，嘗試加上 PROJECTS_DIR 前綴 (如果傳入的是相對路徑)
    if not target_path.exists():
        from src.config import config
        target_path = Path(config.projects_root) / project_name
        if not target_path.exists():
             # 再試試看是否直接傳了專案名
             target_path = Path(config.projects_root) / project_path
    
    if not target_path.exists():
        return f"錯誤：找不到路徑 {project_path} (也找不到 {target_path})"
        
    framework = FrameworkDetector.detect(str(target_path))
    
    if not framework:
        return f"# 無法自動偵測到已知的框架特徵\n# 請手動編輯以下模板\n\nproject: {project_name}\nframework: Unknown\ndirectories:\n  - path: src\n    description: Source Code\n    tags: [source]\n"
        
    suggestion = FrameworkDetector.generate_suggestion(project_name, framework, str(target_path))
    return suggestion

#!/usr/bin/env python3
"""
York MCP Server 主入口
"""

import sys
from pathlib import Path

# 將 src 加入 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from src.agent_server.server import mcp
from src.utils.logger import Logger


def main() -> None:
    """主程式"""
    try:
        Logger.info("Main", "York MCP Server 正在啟動...")
        
        # 啟動 MCP Server
        mcp.run()
        
    except KeyboardInterrupt:
        Logger.info("Main", "收到終止信號，正在關閉...")
    except Exception as e:
        Logger.error("Main", f"發生錯誤: {e}")
        raise


if __name__ == "__main__":
    main()

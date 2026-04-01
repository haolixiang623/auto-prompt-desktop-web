import os
import subprocess
import sys
from pathlib import Path


def test_generate_prompt_exits_nonzero_when_api_key_missing():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "skills" / "doc-extract-prompt-gen" / "generate_prompt.py"
    material_dir = repo_root / "生育津贴支付-材料集" / "出生证明"

    env = dict(os.environ)
    env.pop("DASHSCOPE_API_KEY", None)

    result = subprocess.run(
        [sys.executable, str(script_path), str(material_dir), "出生证明"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "DASHSCOPE_API_KEY" in result.stdout
    assert result.returncode == 1

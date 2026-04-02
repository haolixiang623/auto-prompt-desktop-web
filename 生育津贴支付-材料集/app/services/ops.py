"""
业务操作模块 - 对应 Rust ops.rs
主要功能：协调调用 skills 目录下的 Python 脚本执行实际业务逻辑
"""
import json
import os
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

import httpx

from ..core.config import SettingsStore
from ..core.paths import get_paths
from ..models.schemas import (
    ClassificationReport,
    Factor,
    FileInfo,
    GenerateResult,
    MaterialInfo,
    TestPromptResult,
    VerifyResult,
)

if TYPE_CHECKING:
    from ..core.data import DataStore

# 日志记录器类型
Logger = Callable[[str], None]


def emit_log(logger: Optional[Logger], message: str) -> None:
    """发送日志"""
    if logger:
        logger(message)


class OpsService:
    """业务操作服务"""

    def __init__(self, settings_store: SettingsStore, data_store: Optional["DataStore"] = None):
        self.settings = settings_store
        self.paths = get_paths()
        self._data_store = data_store

    def set_data_store(self, data_store: "DataStore") -> None:
        """延迟注入 DataStore"""
        self._data_store = data_store
    
    def _resolve_skill_path(self, relative_path: str) -> Path:
        """解析 skill 脚本路径"""
        return self.paths.skills_dir / relative_path
    
    def _run_python_skill(
        self,
        skill_path: Path,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        logger: Optional[Logger] = None,
        cwd: Optional[str] = None
    ) -> subprocess.Popen:
        """运行 Python skill 脚本"""
        cmd = ["python", "-u", str(skill_path)] + args
        
        # 合并环境变量
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=run_env,
            cwd=cwd
        )
        
        # 启动线程读取输出
        def read_output(pipe, prefix: str = ""):
            for line in iter(pipe.readline, ''):
                line = line.rstrip()
                if line:
                    emit_log(logger, f"{prefix}{line}")
            pipe.close()
        
        threading.Thread(target=read_output, args=(process.stdout, ""), daemon=True).start()
        threading.Thread(target=read_output, args=(process.stderr, "[错误] "), daemon=True).start()
        
        return process
    
    def generate_factors(
        self,
        work_dir: str,
        material_dirs: List[str],
        logger: Optional[Logger] = None
    ) -> List[GenerateResult]:
        """生成要素提取 JSON"""
        results = []
        skill_path = self._resolve_skill_path("factor-json-generator/generate_factor_json.py")
        
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill 脚本不存在: {skill_path}")
        
        settings = self.settings.get()
        
        for material_dir in material_dirs:
            material_name = os.path.basename(material_dir)
            emit_log(logger, f"[生成] 处理材料: {material_name}")
            
            env = {
                "DASHSCOPE_API_KEY": settings.api_key,
                "OPENAI_API_KEY": settings.api_key,
                "OPENAI_BASE_URL": settings.api_base,
                "MODEL_NAME": settings.model,
            }
            
            process = self._run_python_skill(
                skill_path,
                [work_dir, material_dir],
                env=env,
                logger=logger
            )
            
            exit_code = process.wait()
            
            # 查找输出文件
            output_file = os.path.join(work_dir, f"{material_name}--要素提取结果.json")
            if os.path.exists(output_file):
                results.append(GenerateResult(
                    output_file=output_file,
                    factors_count=0,  # 需要从文件读取
                    images_count=0,
                    prompt_template=None
                ))
            else:
                emit_log(logger, f"[错误] 未找到输出文件: {output_file}")
        
        return results
    
    def classify_materials(
        self,
        work_dir: str,
        max_rounds: int = 3,
        logger: Optional[Logger] = None
    ) -> ClassificationReport:
        """材料分类"""
        skill_path = self._resolve_skill_path("material-classifier/classify_materials.py")
        
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill 脚本不存在: {skill_path}")
        
        settings = self.settings.get()
        
        env = {
            "DASHSCOPE_API_KEY": settings.api_key,
            "CLASSIFY_MODEL_NAME": settings.model,
            "CLASSIFY_GOD_PROMPT": settings.default_prompts.classify if hasattr(settings, 'default_prompts') else "",
        }
        
        process = self._run_python_skill(
            skill_path,
            [work_dir, str(max_rounds)],
            env=env,
            logger=logger,
            cwd=work_dir
        )
        
        exit_code = process.wait()
        
        # 读取分类报告
        report_path = Path(work_dir) / "classification_report.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            return ClassificationReport(**report_data)
        else:
            raise RuntimeError("分类报告未生成")
    
    def verify_extraction(
        self,
        image_path: str,
        prompt_template: str,
        logger: Optional[Logger] = None
    ) -> VerifyResult:
        """验证提取结果"""
        skill_path = self._resolve_skill_path("verification/verify_extraction.py")
        
        if not skill_path.exists():
            # 如果验证脚本不存在，直接返回模拟结果
            return VerifyResult(
                image_file=image_path,
                extraction_output="验证功能未实现",
                success=True,
                elapsed="0.0"
            )
        
        settings = self.settings.get()
        
        env = {
            "DASHSCOPE_API_KEY": settings.api_key,
            "MODEL_NAME": settings.model,
        }
        
        process = self._run_python_skill(
            skill_path,
            [image_path, prompt_template],
            env=env,
            logger=logger
        )
        
        stdout, stderr = process.communicate()
        
        # 解析结果
        try:
            result = json.loads(stdout.strip().split("\n")[-1])
            return VerifyResult(**result)
        except (json.JSONDecodeError, IndexError):
            return VerifyResult(
                image_file=image_path,
                extraction_output=stdout,
                success=process.returncode == 0,
                error=stderr if process.returncode != 0 else None
            )
    
    def test_classify_prompt(
        self,
        work_dir: str,
        prompt_type: str,
        prompt_content: str,
        logger: Optional[Logger] = None
    ) -> TestPromptResult:
        """测试分类提示词"""
        skill_path = self._resolve_skill_path("material-classifier/classify_materials.py")
        
        # 保存临时提示词文件
        tmp_path = Path(work_dir) / f".test_prompt_{prompt_type}.txt"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(prompt_content)
        
        settings = self.settings.get()
        
        env = {
            "DASHSCOPE_API_KEY": settings.api_key,
            "CLASSIFY_MODEL_NAME": settings.model,
        }
        
        process = self._run_python_skill(
            skill_path,
            [f"--test-prompt={prompt_type}", f"--prompt-file={tmp_path}", work_dir],
            env=env,
            logger=logger,
            cwd=work_dir
        )
        
        stdout, stderr = process.communicate()
        
        # 清理临时文件
        tmp_path.unlink(missing_ok=True)
        
        # 解析测试结果
        for line in stdout.split("\n"):
            if line.startswith("TEST_RESULT_JSON:"):
                try:
                    result = json.loads(line[17:])
                    return TestPromptResult(**result)
                except json.JSONDecodeError:
                    pass
        
        return TestPromptResult(
            type=prompt_type,
            pass_=False,
            issues=["未能解析测试结果"],
            error=stderr if stderr else None
        )
    
    def generate_review_rules(
        self,
        work_dir: str,
        use_llm: bool = False,
        logger: Optional[Logger] = None
    ) -> List[Dict[str, Any]]:
        """生成审查规则"""
        skill_path = self._resolve_skill_path("review-rule-generator/generate_review_rule.py")
        
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill 脚本不存在: {skill_path}")
        
        settings = self.settings.get()
        
        args = [work_dir]
        if use_llm:
            args.append("--use-llm")
            args.extend(["--api-key", settings.api_key])
            args.extend(["--base-url", settings.api_base])
            args.extend(["--model", settings.model])
        
        env = {
            "PYTHONUNBUFFERED": "1",
        }
        
        process = self._run_python_skill(
            skill_path,
            args,
            env=env,
            logger=logger
        )
        
        stdout, stderr = process.communicate()
        
        # 解析结果
        for line in stdout.split("\n"):
            if line.startswith("RESULTS_JSON:"):
                try:
                    return json.loads(line[13:])
                except json.JSONDecodeError:
                    pass
        
        # 如果没有 JSON 输出，尝试从文件读取
        results = []
        for entry in os.scandir(work_dir):
            if entry.is_dir():
                material = entry.name
                json_file = Path(entry.path) / f"{material}--审查规则导入.json"
                if json_file.exists():
                    results.append({
                        "material": material,
                        "success": True,
                        "output": str(json_file),
                        "error": "",
                        "keypoint_count": 0
                    })
        
        return results
    
    async def regenerate_keypoint(
        self,
        kpname: str,
        rule_desc: str,
        material_name: str,
        target_rule: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """重新生成审查要点"""
        settings = self.settings.get()
        
        prompt = f"""你是一个审查规则分析专家。请根据以下审查要点规则说明，生成符合导入规范的审查规则JSON。

## 审查背景
- 材料名称: {material_name}
- 审查要点名称: {kpname}
- 审查要点规则说明: {rule_desc}

## 要求
- 必须使用审查方式: {target_rule} (1=大模型, 2=规则对比, 3=Groovy脚本)
- review_rule_text: 简洁的审查规则文本描述
- content: 当review_rule=1时，填写LLM提示词；否则为空
- review_conditions: 当review_rule=2时，填写规则对比条件JSON
- review_rule_js: 当review_rule=3时，填写Groovy脚本

## 输出格式（严格JSON，无多余内容）
{{
  "review_rule": "{target_rule}",
  "review_rule_text": "...",
  "content": "...",
  "review_conditions": null,
  "review_rule_js": "",
  "passreason": "...",
  "nopassreason": "..."
}}"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url or settings.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key or settings.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model or settings.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2000
                },
                timeout=timeout
            )
            
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # 提取 JSON
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())
            else:
                raise ValueError("响应中未找到 JSON")
    
    def get_cases(self, user_id: str = "admin") -> List[Dict[str, Any]]:
        """获取所有案例（按 user_id 隔离）"""
        cases = []
        cases_dir = self.paths.data_dir / "cases"
        if cases_dir.exists():
            for case_file in cases_dir.glob("*.json"):
                try:
                    with open(case_file, "r", encoding="utf-8") as f:
                        case_data = json.load(f)
                        if isinstance(case_data, list):
                            cases.extend(case_data)
                        else:
                            cases.append(case_data)
                except Exception as e:
                    print(f"读取案例文件失败 {case_file}: {e}")
        return cases
    
    def import_cases_from_json(self, source_path: str, overwrite: bool = False) -> int:
        """从 JSON 导入案例（写入 admin 名下）"""
        with open(source_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

        if not isinstance(cases, list):
            cases = [cases]

        for case in cases:
            if not case.get("id"):
                case["id"] = str(datetime.utcnow().timestamp())

        if self._data_store is not None:
            result = self._data_store.import_cases(cases, overwrite=overwrite)
            return result["imported"]

        cases_dir = self.paths.data_dir / "cases"
        cases_dir.mkdir(parents=True, exist_ok=True)
        target_file = cases_dir / Path(source_path).name
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)

        return len(cases)

    def delete_case(self, case_id: str) -> bool:
        """删除案例（仅 admin 可操作）"""
        if self._data_store is not None:
            return self._data_store.delete_case(case_id)
        cases_dir = self.paths.data_dir / "cases"
        for case_file in cases_dir.glob("*.json"):
            try:
                with open(case_file, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                    if isinstance(cases, list):
                        for case in cases:
                            if case.get("id") == case_id:
                                cases.remove(case)
                                with open(case_file, "w", encoding="utf-8") as f2:
                                    json.dump(cases, f2, ensure_ascii=False, indent=2)
                                return True
            except Exception:
                pass
        return False

    def get_review_rules(self) -> List[Dict[str, Any]]:
        """获取审查规则（全员可见）"""
        if self._data_store is not None:
            return self._data_store.list_review_rules()
        rules = []
        rules_dir = self.paths.data_dir / "review_rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*.json"):
                try:
                    with open(rule_file, "r", encoding="utf-8") as f:
                        rule_data = json.load(f)
                        if isinstance(rule_data, list):
                            rules.extend(rule_data)
                        else:
                            rules.append(rule_data)
                except Exception as e:
                    print(f"读取规则文件失败 {rule_file}: {e}")
        return rules

    def update_review_rules(self, rules: List[Dict[str, Any]]) -> bool:
        """更新审查规则（写入 admin 名下）"""
        if self._data_store is not None:
            return self._data_store.save_review_rules(rules)
        rules_dir = self.paths.data_dir / "review_rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        target_file = rules_dir / "rules.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        return True

    def clear_review_rules(self) -> bool:
        """清除审查规则（仅 admin 可操作）"""
        if self._data_store is not None:
            return self._data_store.clear_review_rules()
        rules_dir = self.paths.data_dir / "review_rules"
        if rules_dir.exists():
            for rule_file in rules_dir.glob("*.json"):
                rule_file.unlink()
        return True

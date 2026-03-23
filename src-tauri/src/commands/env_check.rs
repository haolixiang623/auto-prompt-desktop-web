use serde::Serialize;
use std::process::Command;

#[derive(Debug, Serialize, Clone)]
pub struct PythonInfo {
    pub available: bool,
    pub version: String,
    pub installable: bool,
}

#[derive(Debug, Serialize, Clone)]
pub struct PackageStatus {
    pub name: String,
    pub display_name: String,
    pub installed: bool,
    pub version: String,
    pub description: String,
}

#[derive(Debug, Serialize)]
pub struct EnvStatus {
    pub python: PythonInfo,
    pub packages: Vec<PackageStatus>,
}

#[tauri::command]
pub async fn check_environment() -> Result<EnvStatus, String> {
    let python_info = check_python_availability();

    let packages_meta = vec![
        ("openai", "OpenAI SDK", "AI 模型 API 调用，提示词生成与验证的核心依赖"),
        ("openpyxl", "openpyxl", "Excel 文件读写，用于解析 factors.xlsx 要素表"),
        ("pymupdf", "PyMuPDF (fitz)", "PDF 渲染与图片转换，支持 PDF 格式样本"),
    ];

    let mut packages = Vec::new();

    for (pkg_name, display_name, description) in &packages_meta {
        let check_script = format!(
            "import importlib.metadata; print(importlib.metadata.version('{}'))",
            pkg_name
        );
        let python_cmd = get_python_command();
        let result = Command::new(&python_cmd).arg("-c").arg(&check_script).output();

        let status = match result {
            Ok(output) if output.status.success() => {
                let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
                PackageStatus {
                    name: pkg_name.to_string(),
                    display_name: display_name.to_string(),
                    installed: true,
                    version,
                    description: description.to_string(),
                }
            }
            _ => PackageStatus {
                name: pkg_name.to_string(),
                display_name: display_name.to_string(),
                installed: false,
                version: String::new(),
                description: description.to_string(),
            },
        };
        packages.push(status);
    }

    Ok(EnvStatus {
        python: python_info,
        packages,
    })
}

#[derive(Debug, Serialize)]
pub struct InstallResult {
    pub success: bool,
    pub output: String,
    pub requires_restart: bool,
}

fn run_python_command(python_cmd: &str, args: &[&str]) -> Result<std::process::Output, String> {
    Command::new(python_cmd)
        .args(args)
        .output()
        .map_err(|e| format!("执行 Python 失败: {}", e))
}

fn ensure_pip_available(python_cmd: &str) -> Result<String, String> {
    let pip_check = run_python_command(python_cmd, &["-m", "pip", "--version"])?;
    if pip_check.status.success() {
        return Ok(String::new());
    }

    let mut log = String::from("检测到 pip 缺失，正在自动修复...\n");

    let ensurepip = run_python_command(python_cmd, &["-m", "ensurepip", "--upgrade"])?;
    let ensurepip_stdout = String::from_utf8_lossy(&ensurepip.stdout).to_string();
    let ensurepip_stderr = String::from_utf8_lossy(&ensurepip.stderr).to_string();
    log.push_str(&ensurepip_stdout);
    if !ensurepip_stderr.is_empty() {
        if !ensurepip_stdout.is_empty() && !ensurepip_stdout.ends_with('\n') {
            log.push('\n');
        }
        log.push_str(&ensurepip_stderr);
    }

    if !ensurepip.status.success() {
        return Err(format!("自动安装 pip 失败:\n{}", log.trim()));
    }

    let pip_upgrade = run_python_command(python_cmd, &["-m", "pip", "install", "--upgrade", "pip"])?;
    let pip_upgrade_stdout = String::from_utf8_lossy(&pip_upgrade.stdout).to_string();
    let pip_upgrade_stderr = String::from_utf8_lossy(&pip_upgrade.stderr).to_string();
    if !pip_upgrade_stdout.is_empty() {
        if !log.ends_with('\n') {
            log.push('\n');
        }
        log.push_str(&pip_upgrade_stdout);
    }
    if !pip_upgrade_stderr.is_empty() {
        if !log.ends_with('\n') {
            log.push('\n');
        }
        log.push_str(&pip_upgrade_stderr);
    }

    if !pip_upgrade.status.success() {
        return Err(format!("pip 修复后升级失败:\n{}", log.trim()));
    }

    Ok(log)
}

#[tauri::command]
pub async fn install_packages(packages: Vec<String>) -> Result<InstallResult, String> {
    println!("install_packages called with: {:?}", packages);

    if packages.is_empty() {
        return Ok(InstallResult {
            success: true,
            output: "无需安装任何包".to_string(),
            requires_restart: false,
        });
    }

    let python_cmd = get_python_command();
    println!("Using Python command: {}", python_cmd);

    let pip_bootstrap_log = ensure_pip_available(&python_cmd)?;

    let mut cmd = Command::new(&python_cmd);
    cmd.arg("-m").arg("pip").arg("install");
    for pkg in &packages {
        cmd.arg(pkg);
    }

    println!("Executing command: {:?} {:?}", &python_cmd, cmd.get_args());

    let output = cmd.output().map_err(|e| {
        println!("Failed to execute pip command: {}", e);
        format!("执行 pip 失败: {}", e)
    })?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let mut combined = String::new();

    if !pip_bootstrap_log.trim().is_empty() {
        combined.push_str(pip_bootstrap_log.trim());
        combined.push_str("\n\n");
    }

    if stderr.is_empty() {
        combined.push_str(&stdout);
    } else {
        combined.push_str(&stdout);
        if !stdout.is_empty() && !stdout.ends_with('\n') {
            combined.push('\n');
        }
        combined.push_str(&stderr);
    }

    println!("Command exit code: {:?}", output.status.code());
    println!("Command stdout: {}", stdout);
    println!("Command stderr: {}", stderr);

    Ok(InstallResult {
        success: output.status.success(),
        output: combined.trim().to_string(),
        requires_restart: false,
    })
}

#[tauri::command]
pub async fn install_python() -> Result<InstallResult, String> {
    let output = Command::new("winget")
        .arg("install")
        .arg("Python.Python.3.11")
        .arg("--accept-source-agreements")
        .arg("--accept-package-agreements")
        .output()
        .map_err(|e| format!("执行 winget 失败: {}。请确认已安装 Windows Package Manager", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let combined = if stderr.is_empty() {
        stdout
    } else {
        format!("{}\n{}", stdout, stderr)
    };

    Ok(InstallResult {
        success: output.status.success(),
        output: combined.trim().to_string(),
        requires_restart: true,
    })
}

fn check_python_availability() -> PythonInfo {
    if let Some(bundled) = super::path_utils::bundled_python_path() {
        if let Ok(output) = Command::new(&bundled).arg("--version").output() {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
                let version = if stdout.is_empty() { stderr } else { stdout };
                return PythonInfo {
                    available: true,
                    version: format!("{} (内置)", version),
                    installable: false,
                };
            }
        }
    }

    let commands = if cfg!(target_os = "windows") {
        vec!["python", "python3", "py"]
    } else {
        vec!["python3", "python"]
    };

    for cmd in commands {
        if let Ok(output) = Command::new(cmd).arg("--version").output() {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
                let version = if stdout.is_empty() { stderr } else { stdout };
                return PythonInfo {
                    available: true,
                    version,
                    installable: false,
                };
            }
        }
    }

    let installable = if cfg!(target_os = "windows") {
        Command::new("winget").arg("--version").output().is_ok()
    } else {
        Command::new("brew").arg("--version").output().is_ok()
            || Command::new("apt").arg("--version").output().is_ok()
    };

    PythonInfo {
        available: false,
        version: String::new(),
        installable,
    }
}

pub fn get_python_command() -> String {
    if let Ok(explicit) = std::env::var("AUTOPROMPT_PYTHON") {
        if !explicit.trim().is_empty() {
            if Command::new(&explicit)
                .arg("--version")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
            {
                println!("Using AUTOPROMPT_PYTHON: {}", explicit);
                return explicit;
            }
        }
    }

    if let Some(bundled) = super::path_utils::bundled_python_path() {
        println!("Using bundled Python: {}", bundled.display());
        return bundled.to_string_lossy().to_string();
    }

    let commands = if cfg!(target_os = "windows") {
        vec!["python", "python3", "py"]
    } else {
        vec!["python3", "python"]
    };

    for cmd in commands {
        println!("Testing Python command: {}", cmd);
        match Command::new(cmd).arg("--version").output() {
            Ok(output) if output.status.success() => {
                println!("Python command {} works!", cmd);
                return cmd.to_string();
            }
            Ok(_) => println!("Python command {} failed with non-zero exit code", cmd),
            Err(e) => println!("Python command {} failed to execute: {}", cmd, e),
        }
    }

    println!("All Python commands failed, falling back to python3");
    "python3".to_string()
}

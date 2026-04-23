from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime


def get_installed_packages() -> list[dict[str, str]]:
    try:
        from importlib.metadata import distributions
    except Exception:
        try:
            import pkg_resources
        except ImportError as exc:
            raise RuntimeError("无法导入 importlib.metadata 或 pkg_resources，请检查 Python 环境") from exc

        packages = []
        for dist in pkg_resources.working_set:
            packages.append({"name": dist.project_name, "version": str(dist.version)})
        return sorted(packages, key=lambda info: info["name"].lower())
    else:
        packages = []
        for dist in distributions():
            name = dist.metadata.get("Name") or dist.metadata.get("name") or dist.metadata.get("Summary") or "UNKNOWN"
            packages.append({"name": name, "version": dist.version})
        return sorted(packages, key=lambda info: info["name"].lower())


def find_requirements_files(root: str) -> list[str]:
    requirements = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            lower = filename.lower()
            if lower.startswith("requirements") and lower.endswith(".txt"):
                requirements.append(os.path.join(dirpath, filename))
    return sorted(requirements)


def load_requirements(path: str) -> list[str]:
    result = []
    with open(path, "r", encoding="utf-8") as stream:
        for line in stream:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            result.append(text)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描当前项目开发环境中已安装的 Python 包")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument(
        "--include-requirements",
        action="store_true",
        help="同时列出仓库中的 requirements*.txt 文件及其内容",
    )
    parser.add_argument("--root", default=os.getcwd(), help="项目根目录，默认为当前目录")
    parser.add_argument("--download", action="store_true", help="下载所有包到 packages_wheels 目录")
    args = parser.parse_args()

    packages = get_installed_packages()
    requirements_data = None

    if args.include_requirements:
        requirements_data = []
        for path in find_requirements_files(args.root):
            requirements_data.append({"path": path, "entries": load_requirements(path)})

    if args.format == "json":
        output = {"environment": sys.executable, "packages": packages}
        if requirements_data is not None:
            output["requirements_files"] = requirements_data
        content = json.dumps(output, ensure_ascii=False, indent=2)
        print(content)
    else:
        lines = []
        lines.append(f"Python 解释器: {sys.executable}")
        lines.append(f"已安装包数量: {len(packages)}")
        lines.append("-")
        for pkg in packages:
            lines.append(f"{pkg['name']}=={pkg['version']}")

        if requirements_data is not None:
            lines.append("\nrequirements 文件:")
            if not requirements_data:
                lines.append("  未找到 requirements*.txt 文件")
            for item in requirements_data:
                lines.append(f"  {item['path']}")
                for entry in item["entries"]:
                    lines.append(f"    {entry}")

        content = "\n".join(lines)
        print(content)

    # 自动导出 txt 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(args.root, f"packages_scan_{timestamp}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n已导出到: {output_file}")

    # 生成 requirements.txt 文件（可用于 pip install -r requirements.txt）
    req_file = os.path.join(args.root, "requirements.txt")
    with open(req_file, "w", encoding="utf-8") as f:
        for pkg in packages:
            f.write(f"{pkg['name']}=={pkg['version']}\n")
    print(f"已生成 requirements.txt: {req_file}")

    # 下载所有包到 packages_wheels 目录
    if args.download:
        wheels_dir = os.path.join(args.root, "packages_wheels")
        if os.path.exists(wheels_dir):
            shutil.rmtree(wheels_dir)
        os.makedirs(wheels_dir)

        print(f"\n正在下载包到: {wheels_dir}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "download", "-r", req_file, "-d", wheels_dir, "--only-binary=:all:"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            downloaded = os.listdir(wheels_dir)
            print(f"下载完成，共 {len(downloaded)} 个文件")
        else:
            print(f"下载过程中出现警告或错误:\n{result.stderr}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

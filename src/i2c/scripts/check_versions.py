# scripts/check_versions.py
import sys
from packaging.version import Version, InvalidVersion
from importlib.metadata import version as get_version, PackageNotFoundError

REQUIRED_VERSIONS = {
    'groq': '0.23.1',
    'agno': '>=0.1.0',
    'torch': '==2.2.2',
}
from i2c.bootstrap import initialize_environment
initialize_environment()
def compare_versions(installed, requirement):
    try:
        installed_v = Version(installed)
    except InvalidVersion:
        return False

    if requirement.startswith('>='):
        return installed_v >= Version(requirement[2:])
    elif requirement.startswith('=='):
        return installed_v == Version(requirement[2:])
    elif requirement.startswith('<'):
        return installed_v < Version(requirement[1:])
    else:
        return installed_v == Version(requirement)

def check_versions():
    print(f"✓ Python {sys.version.split()[0]}")
    issues = []

    for package, requirement in REQUIRED_VERSIONS.items():
        try:
            installed = get_version(package)
            if not compare_versions(installed, requirement):
                issues.append(f"{package}: installed {installed}, requires {requirement}")
            else:
                print(f"✓ {package} {installed}")
        except PackageNotFoundError:
            issues.append(f"{package}: not installed, requires {requirement}")

    if issues:
        print("\n⚠️ Version issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n⚠️ Some package versions don't match requirements, but we'll continue anyway.")
    else:
        print("\n✅ All versions correct!")

if __name__ == "__main__":
    check_versions()

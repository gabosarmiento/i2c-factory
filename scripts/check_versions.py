# scripts/check_versions.py
import pkg_resources
import sys

REQUIRED_VERSIONS = {
    'groq': '0.23.1',
    'agno': '>=0.1.0',
    'numpy': '1.26.4',
    # Add other critical packages
}

def check_versions():
    """Check if installed versions match requirements"""
    issues = []
    
    for package, required in REQUIRED_VERSIONS.items():
        try:
            installed_version = pkg_resources.get_distribution(package).version
            
            if required.startswith('>='):
                min_version = required[2:]
                if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(min_version):
                    issues.append(f"{package}: installed {installed_version}, requires >={min_version}")
            elif installed_version != required:
                issues.append(f"{package}: installed {installed_version}, requires {required}")
            else:
                print(f"✓ {package} {installed_version}")
        except pkg_resources.DistributionNotFound:
            issues.append(f"{package}: not installed, requires {required}")
    
    if issues:
        print("\n⚠️ Version issues found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ All versions correct!")

if __name__ == "__main__":
    check_versions()
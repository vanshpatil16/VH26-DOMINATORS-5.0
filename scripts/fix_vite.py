#!/usr/bin/env python3
"""Fix vite.config.ts and package.json — called by setup.sh"""
import json, re, sys, os

frontend_dir = sys.argv[1] if len(sys.argv) > 1 else "frontend"

# --- Fix vite.config.ts ---
config_path = os.path.join(frontend_dir, "vite.config.ts")
if os.path.exists(config_path):
    with open(config_path) as f:
        content = f.read()
    content = re.sub(r".*@builder\.io/vite-plugin-jsx-loc.*\n", "", content)
    content = content.replace("jsxLocPlugin(), ", "")
    content = content.replace(", jsxLocPlugin()", "")
    content = content.replace("jsxLocPlugin()", "")
    if "const plugins" not in content and "export default defineConfig" in content:
        line = "const plugins = [react(), tailwindcss(), vitePluginManusRuntime(), vitePluginManusDebugCollector(), vitePluginStorageProxy(), vitePluginCodegateApi(), vitePluginAdminApi()];\n\n"
        content = content.replace("export default defineConfig({", line + "export default defineConfig({")
    with open(config_path, "w") as f:
        f.write(content)
    print("  vite.config.ts fixed")

# --- Fix package.json ---
pkg_path = os.path.join(frontend_dir, "package.json")
if os.path.exists(pkg_path):
    with open(pkg_path) as f:
        pkg = json.load(f)
    pkg.get("devDependencies", {}).pop("@builder.io/vite-plugin-jsx-loc", None)
    pkg["devDependencies"] = {k: v for k, v in pkg.get("devDependencies", {}).items() if v}
    pkg["dependencies"] = {k: v for k, v in pkg.get("dependencies", {}).items() if v}
    with open(pkg_path, "w") as f:
        json.dump(pkg, f, indent=2)
    print("  package.json fixed")

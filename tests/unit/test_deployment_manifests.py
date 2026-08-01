"""Structural guards for the one-click deployment path.

``scripts/deployment/one-click-deploy.sh`` aborted at its first gate because
``REQUIRED_FILES`` named paths that had moved under ``infrastructure/`` and two
modules that never existed. Once past that gate it would have rolled out a
manifest describing the Python image as a Node service on port 3000, and a
sibling Deployment mounting a ConfigMap that is defined nowhere in the
repository.

Every assertion here is derived from the repository rather than restated by
hand, so the checks keep tracking the deployment as it moves.
"""

import re
import unittest
from pathlib import Path

import yaml


def _repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "scripts" / "deployment" / "one-click-deploy.sh").exists():
            return candidate
    raise AssertionError("repository root not found")


REPO_ROOT = _repo_root()
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deployment" / "one-click-deploy.sh"
PRODUCTION_DIR = REPO_ROOT / "infrastructure" / "k8s" / "production"
MONITORING_DIR = REPO_ROOT / "infrastructure" / "k8s" / "monitoring"


def _script():
    return DEPLOY_SCRIPT.read_text(encoding="utf-8")


def _script_variables(script):
    """Collect the literal top-level assignments the script's paths are built from."""

    variables = {}
    for name, value in re.findall(
        r'^([A-Z_]+)="([^"$]*)"$', script, flags=re.MULTILINE
    ):
        variables[name] = value
    return variables


def _expand(value, variables):
    def replace(match):
        name = match.group(1) or match.group(2)
        if name not in variables:
            raise AssertionError(f"unresolved shell variable in path: ${name}")
        return variables[name]

    return re.sub(r'\$\{([A-Z_]+)\}|\$([A-Z_]+)', replace, value)


def _manifests(directory):
    for path in sorted(directory.glob("*.yaml")):
        for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if document:
                yield path, document


class DeployScriptPathTests(unittest.TestCase):
    def test_required_files_all_exist(self):
        script = _script()
        variables = _script_variables(script)
        block = re.search(
            r"REQUIRED_FILES=\(\s*(.*?)\s*\)", script, flags=re.DOTALL
        )
        self.assertIsNotNone(block, "REQUIRED_FILES array not found")

        entries = re.findall(r'"([^"]+)"', block.group(1))
        self.assertGreater(len(entries), 0)

        for entry in entries:
            with self.subTest(entry=entry):
                resolved = REPO_ROOT / _expand(entry, variables)
                self.assertTrue(
                    resolved.is_file(),
                    f"REQUIRED_FILES names {entry}, which does not exist",
                )

    def test_every_referenced_path_exists(self):
        """`docker build -f` and `kubectl apply -f` targets must be real."""

        script = _script()
        variables = _script_variables(script)
        referenced = re.findall(
            r'(?:docker build|kubectl apply)[^\n]*?-f "([^"]+)"', script
        )
        self.assertGreater(len(referenced), 0)

        for entry in referenced:
            if entry == "-":  # `kubectl apply -f -` reads stdin.
                continue
            with self.subTest(entry=entry):
                resolved = REPO_ROOT / _expand(entry, variables).rstrip("/")
                self.assertTrue(
                    resolved.exists(),
                    f"script applies {entry}, which does not exist",
                )

    def test_script_runs_from_the_repository_root(self):
        """Relative paths are only meaningful once the script anchors itself."""

        script = _script()
        self.assertIn('REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")', script)
        self.assertIn('cd "$REPO_ROOT"', script)
        self.assertLess(
            script.index('cd "$REPO_ROOT"'),
            script.index("REQUIRED_FILES=("),
        )


class ProductionManifestTests(unittest.TestCase):
    def _documents(self):
        return [document for _, document in _manifests(PRODUCTION_DIR)]

    def _deployments(self):
        return [d for d in self._documents() if d.get("kind") == "Deployment"]

    def _services(self):
        return [d for d in self._documents() if d.get("kind") == "Service"]

    def test_mounted_configmaps_are_defined_in_the_repository(self):
        """A pod mounting an undefined ConfigMap can never start.

        The removed `mcp-server` Deployment mounted `mcp-server-code`, which no
        manifest creates, so `kubectl rollout status` could only ever time out.
        """

        defined = set()
        for directory in (PRODUCTION_DIR, MONITORING_DIR):
            for _, document in _manifests(directory):
                if document.get("kind") == "ConfigMap":
                    defined.add(document["metadata"]["name"])

        for path, document in _manifests(PRODUCTION_DIR):
            if document.get("kind") != "Deployment":
                continue
            volumes = (
                document["spec"]["template"]["spec"].get("volumes") or []
            )
            for volume in volumes:
                config_map = volume.get("configMap")
                if not config_map:
                    continue
                with self.subTest(path=path.name, name=config_map["name"]):
                    self.assertIn(
                        config_map["name"],
                        defined,
                        f"{path.name} mounts ConfigMap "
                        f"{config_map['name']}, which is defined nowhere",
                    )

    def test_service_target_ports_match_a_container_port(self):
        """Traffic sent to a port no container listens on is silently dropped."""

        container_ports = {}
        for deployment in self._deployments():
            app = deployment["spec"]["selector"]["matchLabels"]["app"]
            ports = set()
            for container in deployment["spec"]["template"]["spec"]["containers"]:
                for port in container.get("ports") or []:
                    ports.add(port["containerPort"])
            container_ports[app] = ports

        for service in self._services():
            app = service["spec"]["selector"]["app"]
            with self.subTest(service=service["metadata"]["name"]):
                self.assertIn(
                    app,
                    container_ports,
                    f"service selects app={app}, which no Deployment provides",
                )
                for port in service["spec"]["ports"]:
                    self.assertIn(
                        port["targetPort"],
                        container_ports[app],
                        f"targetPort {port['targetPort']} is not exposed by "
                        f"any {app} container",
                    )

    def test_container_port_matches_the_image_it_runs(self):
        """The manifest and the Dockerfile must agree on the listening port."""

        dockerfile = (
            REPO_ROOT / "infrastructure" / "docker" / "Dockerfile.production"
        ).read_text(encoding="utf-8")
        exposed = {
            int(port)
            for port in re.findall(r"^EXPOSE\s+(\d+)", dockerfile, re.MULTILINE)
        }
        self.assertTrue(exposed, "Dockerfile.production declares no EXPOSE")

        for deployment in self._deployments():
            if deployment["metadata"]["name"] != "enhanced-framework":
                continue
            for container in deployment["spec"]["template"]["spec"]["containers"]:
                for port in container.get("ports") or []:
                    self.assertIn(
                        port["containerPort"],
                        exposed,
                        "enhanced-framework listens on "
                        f"{port['containerPort']} but the image exposes "
                        f"{sorted(exposed)}",
                    )

    def test_probe_paths_are_served_by_the_application(self):
        """A probe on an unrouted path fails forever and blocks the rollout."""

        main = (
            REPO_ROOT / "src" / "youtube_extension" / "main.py"
        ).read_text(encoding="utf-8")
        routes = set(re.findall(r'@app\.get\(\s*"([^"]+)"', main))
        self.assertIn("/health", routes, "sanity: /health route not found")

        for deployment in self._deployments():
            if deployment["metadata"]["name"] != "enhanced-framework":
                continue
            for container in deployment["spec"]["template"]["spec"]["containers"]:
                for probe in ("livenessProbe", "readinessProbe"):
                    spec = container.get(probe)
                    if not spec or "httpGet" not in spec:
                        continue
                    with self.subTest(probe=probe):
                        self.assertIn(
                            spec["httpGet"]["path"],
                            routes,
                            f"{probe} targets {spec['httpGet']['path']}, "
                            "which the application does not route",
                        )

    def test_no_manifest_references_a_removed_service(self):
        """Nothing should point at the phantom MCP server that was removed."""

        for directory in (PRODUCTION_DIR, MONITORING_DIR):
            for path in sorted(directory.glob("*.yaml")):
                with self.subTest(path=path.name):
                    self.assertNotIn(
                        "mcp-server", path.read_text(encoding="utf-8")
                    )


if __name__ == "__main__":
    unittest.main()

"""Guards for the gitleaks allowlist used by the ``gitleaks (working tree)`` job.

``uv.lock`` records every artifact as a PyPI download URL whose path embeds the
artifact's own content hash. One of those hex segments has enough length and
entropy to trip the default ``square-access-token`` rule, so the secret scan
failed on every pull request regardless of its diff.

The suppression has to stay narrow. Excluding the lockfile wholesale would also
hide a private index URL carrying real credentials, which is exactly the kind of
secret this job exists to catch. These checks pin the shape of the fix:

* the lockfile itself is still scanned,
* the suppression is anchored to the public PyPI CDN host, and
* the workflow actually loads this configuration.
"""

import tomllib
import unittest
from pathlib import Path


def _repo_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".gitleaks.toml").exists():
            return candidate
    raise AssertionError("repository root not found")


REPO_ROOT = _repo_root()
CONFIG_PATH = REPO_ROOT / ".gitleaks.toml"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "secret-scan.yml"

# Lockfiles are the files the false positive lives in. They must never be
# allowlisted by path, because a private index URL embeds its credentials
# inline and would then go unreported.
SCANNED_LOCKFILES = ("uv.lock", "package-lock.json", "poetry.lock")


def _config():
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


class SecretScanConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = _config()
        self.allowlist = self.config.get("allowlist", {})

    def test_config_extends_the_default_ruleset(self):
        """Dropping ``useDefault`` would silently disable every built-in rule."""
        self.assertTrue(
            self.config.get("extend", {}).get("useDefault"),
            ".gitleaks.toml must extend the default gitleaks ruleset",
        )

    def test_lockfiles_are_not_excluded_by_path(self):
        """A path exclusion would hide real credentials in the same file."""
        paths = self.allowlist.get("paths", [])
        for lockfile in SCANNED_LOCKFILES:
            for pattern in paths:
                self.assertNotIn(
                    lockfile,
                    pattern,
                    f"{lockfile} must stay scanned; found path allowlist "
                    f"{pattern!r}. Narrow the suppression to the benign "
                    f"pattern instead of excluding the file.",
                )

    def test_pypi_suppression_is_anchored_to_the_public_cdn_host(self):
        """The regex must require the CDN host, not just a hash-shaped string."""
        regexes = self.allowlist.get("regexes", [])
        self.assertTrue(
            any("files" in r and "pythonhosted" in r for r in regexes),
            "expected an allowlist regex anchored on files.pythonhosted.org; "
            f"got {regexes!r}",
        )
        for regex in regexes:
            if "pythonhosted" not in regex:
                continue
            self.assertIn(
                "/packages/",
                regex,
                "the suppression must require the /packages/ URL prefix so it "
                "cannot match arbitrary text mentioning the host",
            )

    def test_regex_allowlist_matches_whole_lines(self):
        """``regexes`` compare against the extracted secret unless retargeted.

        The secret here is a bare hex path segment, so the host anchor only
        works when the allowlist is evaluated against the full line.
        """
        if not self.allowlist.get("regexes"):
            self.skipTest("no regex allowlist configured")
        self.assertEqual(
            self.allowlist.get("regexTarget"),
            "line",
            "regexTarget must be 'line' for the host-anchored regex to apply",
        )

    def test_workflow_loads_this_configuration(self):
        """An allowlist the scan never reads is not a fix."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "--config .gitleaks.toml",
            workflow,
            "secret-scan.yml must run gitleaks with --config .gitleaks.toml",
        )


if __name__ == "__main__":
    unittest.main()

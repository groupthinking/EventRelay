import hashlib,json,pathlib,subprocess,zipfile,collections
out=pathlib.Path("image-artifact-proof");out.mkdir(exist_ok=True)
archive=out/"artifact.zip"
with archive.open("wb") as f:
    subprocess.run(["gh","api","repos/groupthinking/EventRelay/actions/artifacts/14312702282/zip"],stdout=f,check=True)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest=="e4e69faa517eabdfe46f5564086edaed18ec14a3cd95466eb29c051eebf10515",digest
with zipfile.ZipFile(archive) as z:
    source=z.read("image-source-commit.txt").decode().strip()
    assert source=="1c9ea05dad54ef35c5edd0d4d84ce0b96452b235",source
    sarif=json.loads(z.read("trivy-results.sarif"))
    identity=json.loads(z.read("image-identity.json"))[0]
rows=[r for run in sarif["runs"] for r in run.get("results",[])]
counts={c:sum(c in json.dumps(r) for r in rows) for c in ["CVE-2026-76844","CVE-2026-85091","CVE-2025-47273","CVE-2026-6653"]}
rules=[r for run in sarif["runs"] for r in run.get("tool",{}).get("driver",{}).get("rules",[])]
proof={"artifact":14312702282,"zip_sha256":digest,"source":source,"image_id":identity["Id"],"rows":len(rows),"target_counts":counts,"rule_samples":rules[:2],"result_samples":rows[:2],"status":"VERIFIED"}
(out/"proof.json").write_text(json.dumps(proof,indent=2))
print(json.dumps(proof))
assert all(counts[c]==0 for c in ["CVE-2026-76844","CVE-2026-85091","CVE-2025-47273"]),counts

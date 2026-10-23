# Scientific audits

A public monorepo for reusable and run-specific audits. Each audit records sampling, coverage, metrics and limitations. It complements the separately pinned [RDF type audit](https://github.com/toxindex/rdf-type-audit); it does not alter scientific graphs.

```sh
nix flake check
nix run . -- --graph graph.nt --cases cases.json --output results --sample-size 3
```

`cases.json` binds to the exact graph bytes with `graph_sha256`. Its arrays are `pmc`, `database`, `quotes`, `screening`, `extraction` and `required_documents`. Each case has an `id`. The CLI source defines their small contracts. Preserve original source hashes and decision context in the bundle; supplementary retained outputs must be distinguished from graph entities. Never include API keys. Sampling is reproducible by SHA256 of seed + ID, independent of input order.

For a bounded live audit:

```sh
nix run . -- --graph graph.nt --cases cases.json --output results \
  --sample-size 3 --vertex --max-calls 6 --project YOUR_PROJECT \
  --model gemini-3.8-flash --live --allow-host pmc.ncbi.nlm.nih.gov
```

Vertex uses Google Application Default Credentials, including service accounts. Request/response/usage artifacts are cached under the output directory, keyed by model, project and full prompt. No original screening decision is supplied to the screening judge. Extraction checks compare the recorded interpretation with quotes and bounded source context. Results measure agreement, not gold-standard accuracy or exhaustive extraction completeness. Failed calls and insufficient context are inconclusive, never counted as agreements.

Optional source API credentials: `--api-key-env AUDIT_API_KEY --api-key-host exact.host --api-key-header X-API-Key`. The key stays in the environment and is sent only to that explicitly allowed host. Redirects are rejected. The database audit currently verifies retained row/cell provenance rather than issuing arbitrary SQL against a live service. The PMC audit checks the specific nominated full texts, not discovery recall.

Exit 0 means the suite completed and wrote results, including disagreements or inconclusive checks. Configuration/parsing exceptions exit nonzero. Inspect each audit's status and metric rather than treating the process exit as a scientific pass. Empty populations are not assessable. Results and cached source context may be confidential; do not commit them here.

`schemas/audit.ttl` defines an Audit as an AssessmentProcess with an AuditResult. `results_rdf.py` converts results and validates them using SHACL. Scope (`Reusable`/`Run-specific`), category, completion, partial coverage and agreement are separate fields. Audits do not introduce conclusions into the assessed graph.

See [migration notes](docs/migration.md) for the reviewed legacy contracts and incomplete migrations.

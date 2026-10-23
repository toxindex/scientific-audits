# Scientific audits

A public monorepo for reusable and run-specific audits. Each audit records sampling, coverage, metrics and limitations. It complements the separately pinned [RDF type audit](https://github.com/toxindex/rdf-type-audit); it does not alter scientific graphs.

```sh
nix flake check
nix run . -- --graph graph.nt --cases cases.json --output results --sample-size 3
```

`cases.json` binds to the exact graph bytes with `graph_sha256`. Its arrays are `pmc`, `database`, `quotes`, `screening` and `extraction`. Each case has an `id`. The CLI source defines their small contracts. Preserve original source hashes and decision context in the bundle; supplementary retained outputs must be distinguished from graph entities. Never include API keys. Sampling is reproducible by SHA256 of seed + ID, independent of input order.

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

Export and validate the audit receipts as RDF (separate from the scientific graph):

```sh
nix develop -c python results_rdf.py out/results.json \
  --revision "$(git rev-parse HEAD)" --graph urn:example:graph \
  --output out/audits.ttl
```

`schemas/audit.ttl` defines the proposed Audit vocabulary and SHACL shapes.
The namespace is a vocabulary proposal; it is not a claim of W3ID registration.
Each execution records its procedure, agent, decision context, graph and code
hashes, scope, sampling counts and result. Agreement is a fraction with a visible
denominator, not a claim of sensitivity or specificity. Audits may disagree
without the audit command itself failing.

Run-specific scientific expectations belong in the private workflow repository, not this reusable suite.

## LinkML entity validation

```sh
nix run .#linkml-check -- --graph graph.nt --schema ontology.yaml --schema workflow.yaml --output audit
```

This uses pinned LinkML, pySHACL and the Oxigraph RDFLib adapter. The first invocation installs the locked Python environment into the user cache. Subsequent runs reuse it. Quick mode checks **all subjects for types and declared classes**, then samples five subjects per type for constraint validation. `--full` requests all constraint targets. Both have a default 115-second audit budget; `--timeout` changes it explicitly. Incomplete or sampled runs cannot earn a full pass. Runtime and phase timings are retained.

`name` is a short audit identifier, separate from its description. Audits may link to subaudits; the LinkML check reports typing, declared types, shape coverage and per-class constraint results. Blank-node diagnostics retain identifiers instead of recursively printing or copying reachable data. This affects report formatting only, not constraint evaluation.

The validator checks unsupported expression coverage separately. Literal `equals_expression` constants are compiled to SHACL `hasValue`; unhandled expressions and uniqueness declarations are reported rather than silently certified. RDF 1.1 string literal normalization avoids false differences between plain strings and `xsd:string`. Full validation uses all subjects; quick sampling is stable for the exact N-Triples snapshot, including its blank-node labels.

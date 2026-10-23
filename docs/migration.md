# Sage endocrine test migration

Reviewed `endocrine-review-dvc`, `endocrine-review-dvc-spark` and `endocrine-review-nf` under the local `embsi-worfklows/workflows` checkout. These audits adapt the scientific contracts to portable inputs; they do not import the old engines or claim equivalence of their implementation-specific tests.

| Legacy contract | Portable audit | Scope / limitation |
|---|---|---|
| `test_resource_types`: every emitted class is declared | Existing `toxindex/rdf-type-audit` | Reusable; keep independently pinned repo |
| `test_gather_reliability`: quoted passage occurs in retained full text | `quotes` | Reusable; whitespace-normalized text containment |
| `test_adapters`: table identity, columns, primary keys and recorded samples | `database` | Reusable; retained cells/key consistency; live source requery remains separate |
| `test_flow_required_literature`: nominated publications are present | `required-documents` | Run-specific n-hexane requirements; identifier presence only, not ranking/inclusion |
| `test_pubmed`: complete paging, abstracts, repeated-page stopping | PMC identity/title/abstract/body retrieval check added | Reusable; partial migration, pagination/recall not certified |
| `test_tox21`, `test_chemharmony`, `test_ice_endocrine` | Catalogued as run-specific legacy expectations | Not automatically executed against new database versions; expected counts/outcomes need versioned source fixtures |
| `test_evidence_design`, synthesis/AOP tests | Deferred | Depend on their originating application contracts; do not substitute lexical rules |
| `test_panel_coverage` unseen-brick assertion | Rejected as written | It computes unseen values then checks whether those are seen, so its assertion cannot fail |

The screening audit records supplementary retained decision provenance because the selected scientific RDF may omit screening assessments. A separate RDF projection check reports this omission. A model judge is not a human gold standard. Sampling reports population, selected, evaluated and inconclusive counts separately.

"""Validate all RDF subjects against current LinkML-generated SHACL constraints."""
import argparse,hashlib,json,time,signal
from pathlib import Path
from unittest.mock import patch
from collections import defaultdict
from importlib.metadata import version
from rdflib import Graph,RDF,RDFS,URIRef,BNode,Namespace,Literal,XSD
import pyoxigraph
from oxrdflib import OxigraphStore
from linkml.generators.shaclgen import ShaclGenerator
from linkml_runtime.utils.schemaview import SchemaView
from pyshacl import validate
SH=Namespace('http://www.w3.org/ns/shacl#')
class SnapshotGraph(Graph):
 # Immutable during validation: avoid COUNT(*) scans on each truth test.
 def __len__(self):
  if hasattr(self,'triple_count'):return self.triple_count
  return super().__len__()
 def __bool__(self):return len(self)>0

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def child(name,description,count,failures,samples=()):
 return {'name':name,'description':description,'status':'fail' if failures else 'pass' if count else 'not-applicable','evaluated':count,'failures':failures,'samples':list(samples)[:20]}
def run(graph_path,schemas,out,full=False,per_type=5):
 start=time.time();timings={};out.mkdir(parents=True,exist_ok=True)
 shapes=Graph();allowed=set();schema_hashes={};names={};views=[];gaps=[]
 for path in schemas:
  schema_hashes[str(path.name)]=digest(path);view=SchemaView(str(path));views.append(view)
  for c in view.all_classes().values():
   uri=URIRef(view.get_uri(c,expand=True));allowed.add(uri);names[uri]=c.name
  shapes.parse(data=ShaclGenerator(str(path),closed=False).serialize(),format='turtle')
 # LinkML's generator omits general equals_expression constraints. Support
 # literal constants explicitly; flag anything that cannot be compiled safely.
 for view in views:
  for c in view.all_classes().values():
   uri=URIRef(view.get_uri(c,expand=True))
   if c.unique_keys:gaps.append(str(uri)+': unique_keys require a dedicated graph constraint')
   for slot in view.class_induced_slots(c.name):
    expr=slot.equals_expression
    if expr is None:continue
    try:
     value=json.loads(expr)
     if isinstance(value,(dict,list)) or value is None:raise ValueError()
     path=URIRef(view.get_uri(slot,expand=True))
     props=[p for p in shapes.objects(uri,SH.property) if shapes.value(p,SH.path)==path]
     if not props:raise ValueError()
     for prop in props:shapes.add((prop,SH.hasValue,Literal(value)))
    except (ValueError,TypeError):gaps.append(str(uri)+'.'+slot.name+': unsupported equals_expression '+str(expr))
 # RDF 1.1 plain strings and xsd:string are the same RDF literal. Oxigraph
 # returns typed strings; normalize generated shape literals to the same form.
 for s,p,o in list(shapes):
  if isinstance(o,Literal) and o.datatype is None and o.language is None:
   shapes.remove((s,p,o));shapes.add((s,p,Literal(str(o),datatype=XSD.string)))
 # Abstract LinkML classes can still appear as explicitly asserted supertypes.
 for c in allowed:
  if (c,RDF.type,SH.NodeShape) in shapes:shapes.add((c,SH.targetClass,c))
 shapes.serialize(destination=out/'shapes.ttl',format='turtle')
 print('Loading full RDF snapshot',flush=True)
 timings['compile_shapes_seconds']=time.time()-start;phase=time.time()
 backend=pyoxigraph.Store();context=pyoxigraph.NamedNode('urn:audit:snapshot')
 backend.extend(pyoxigraph.Quad(q.subject,q.predicate,q.object,context) for q in pyoxigraph.parse(path=graph_path,format=pyoxigraph.RdfFormat.N_TRIPLES if graph_path.suffix=='.nt' else pyoxigraph.RdfFormat.TURTLE,rename_blank_nodes=False))
 g=SnapshotGraph(store=OxigraphStore(store=backend),identifier=URIRef(context.value));g.triple_count=len(g)
 timings['load_graph_seconds']=time.time()-phase;phase=time.time()
 subjects=set(g.subjects());types=defaultdict(set)
 for s,t in g.subject_objects(RDF.type):types[s].add(t)
 missing=sorted(str(s) for s in subjects if not types[s]);unknown=sorted((str(s),str(t)) for s,ts in types.items() for t in ts if t not in allowed or not isinstance(t,URIRef))
 covered=set(shapes.objects(None,SH.targetClass));uncovered=sorted(str(t) for ts in types.values() for t in ts if t in allowed and t not in covered)
 checks=[child('compiler-coverage','No unsupported schema constraints were silently omitted.',len(schemas),len(gaps),gaps),child('has-type','Every RDF subject, including blank nodes, has an explicit rdf:type.',len(subjects),len(missing),missing),child('declared-types','Every explicit type is a class declared by the supplied LinkML schemas.',sum(map(len,types.values())),len(unknown),unknown),child('shape-coverage','Every declared type used in this graph has a generated target shape.',len({t for ts in types.values() for t in ts if t in allowed}),len(set(uncovered)),sorted(set(uncovered)))]
 timings['identity_checks_seconds']=time.time()-phase;phase=time.time()
 targets=defaultdict(set)
 for node,ts in types.items():
  for t in ts:targets[t].add(node)
 selected=set(subjects) if full else set()
 sampled_shapes=shapes
 if not full:
  sampled_shapes=Graph()
  for triple in shapes:sampled_shapes.add(triple)
  for shape,c in list(shapes.subject_objects(SH.targetClass)):
   sampled_shapes.remove((shape,SH.targetClass,c))
   nodes=sorted(targets[c],key=lambda n:hashlib.sha256(str(n).encode()).digest())[:per_type]
   selected.update(nodes)
   for node in nodes:sampled_shapes.add((shape,SH.targetNode,node))
 print(f'Validating {len(selected)} / {len(subjects)} entity targets',flush=True)
 progress={'name':'linkml-check','description':'validates every entity against the linkml requirements','status':'running','partial':True,'subaudits':checks,'duration_seconds':time.time()-start,'timings':timings}
 (out/'result.json').write_text(json.dumps(progress,indent=2))
 # Change report rendering only: keep blank-node identifiers, never recursively
 # copy or print their entire reachable subgraph. Constraint evaluation is unchanged.
 with patch('pyshacl.constraints.constraint_component.stringify_node',lambda graph,node,*args,**kw:node.n3()[:500]), patch('pyshacl.validator.clone_blank_node',lambda source,node,target,*args,**kw:node):
  conforms,report,_=validate(g,shacl_graph=sampled_shapes,inference='none',advanced=False,abort_on_first=False,allow_warnings=False,allow_infos=False)
 timings['constraints_seconds']=time.time()-phase;phase=time.time()
 report.serialize(destination=out/'validation-report.ttl',format='turtle')
 owners=defaultdict(set)
 for shape,c in shapes.subject_objects(SH.targetClass):
  owners[shape].add(c)
  for prop in shapes.objects(shape,SH.property):owners[prop].add(c)
 by_class=defaultdict(list);failures=[]
 for r in report.subjects(RDF.type,SH.ValidationResult):
  row={k:str(report.value(r,p) or '') for k,p in [('entity',SH.focusNode),('path',SH.resultPath),('constraint',SH.sourceConstraintComponent),('message',SH.resultMessage)]}
  failures.append(row)
  for c in owners[report.value(r,SH.sourceShape)]:by_class[c].append(row)
 children=[]
 for c in sorted(covered,key=str):
  count=len(targets[c] & selected)
  if not count:continue
  children.append(child(names.get(c,str(c)),'Constraints for '+str(c),count,len(by_class[c]),by_class[c]))
 checks.append(dict(child('ontology-constraints','LinkML SHACL requirements: cardinality, datatype, ranges, patterns, enums and other generated constraints.',len(subjects),len(failures),failures),status='pass' if conforms else 'fail',subaudits=children))
 data={'name':'linkml-check','description':'validates every entity against the linkml requirements','status':('pass' if full else 'partial') if all(c['status']=='pass' for c in checks) else 'fail','partial':not full,'sampling':{'method':'all entities' if full else 'deterministic SHA256 per explicit class','population':len(subjects),'selected':len(selected),'per_type':None if full else per_type},'timings':timings,'graph_sha256':digest(graph_path),'schema_sha256':schema_hashes,'implementation_sha256':digest(__file__),'dependencies':{k:version(k) for k in ['linkml','linkml-runtime','pyshacl','rdflib','oxrdflib','pyoxigraph']},'counts':{'triples':len(g),'entities':len(subjects),'untyped_entities':len(missing),'unknown_type_assertions':len(unknown),'constraint_violations':len(failures)},'subaudits':checks,'duration_seconds':time.time()-start,'scope':'Every RDF subject, including blank nodes. Object-only external references and vocabulary IRIs are not treated as local entity records. Extra predicates are allowed; all declared constraints are generated with the official LinkML SHACL generator. No graph repair or data inference. Required fields not authored in LinkML cannot be inferred by this audit.','artifacts':{'shapes':'shapes.ttl','report':'validation-report.ttl'}}
 (out/'result.json').write_text(json.dumps(data,indent=2));return data
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--graph',type=Path,required=True);p.add_argument('--schema',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full',action='store_true');p.add_argument('--per-type',type=int,default=5);p.add_argument('--timeout',type=int,default=115);a=p.parse_args()
 start=time.time()
 def timed_out(*_):raise TimeoutError('Audit time budget exceeded')
 signal.signal(signal.SIGALRM,timed_out);signal.alarm(a.timeout)
 try:r=run(a.graph,a.schema,a.output,a.full,a.per_type);print(json.dumps(r['counts']));raise SystemExit(0 if r['status']=='pass' else 1)
 except Exception as e:
  a.output.mkdir(parents=True,exist_ok=True);prior=json.loads((a.output/'result.json').read_text()) if (a.output/'result.json').exists() else {}; (a.output/'result.json').write_text(json.dumps({**prior,'duration_seconds':time.time()-start,'name':'linkml-check','description':'validates every entity against the linkml requirements','status':'error','partial':True,'error':type(e).__name__+': '+str(e)},indent=2));raise

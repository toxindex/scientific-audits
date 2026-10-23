import argparse,json,hashlib
from pathlib import Path
from decimal import Decimal
from rdflib import Graph,Namespace,URIRef,Literal,RDF,RDFS,XSD
from pyshacl import validate
A=Namespace('https://w3id.org/toxindex/audit/');T=Namespace('urn:toxindex:')
def convert(data,revision,graph_iri):
 g=Graph();g.bind('aud',A);g.bind('ti',T)
 for item in data['audits']:
  node=URIRef('urn:toxindex:audit:'+hashlib.sha256((data['graph_sha256']+revision+item['id']+data['cases_sha256']).encode()).hexdigest());result=URIRef(str(node)+':result');s=item['sampling'];m=item['metrics']
  for p,o in [(RDF.type,A.Audit),(RDFS.label,Literal(item['label'])),(A.scope,Literal(item['scope'])),(A.category,Literal(item['category'])),(T['assessment-subject'],URIRef(graph_iri)),(A.graphSha256,Literal(data['graph_sha256'])),(A.codeRepository,URIRef(item['repository'])),(A.codeRevision,Literal(revision)),(T['applies-procedure'],URIRef(item['repository']+'/blob/'+revision+'/audits.py')),(T.agent,URIRef('urn:toxindex:audit-agent:'+ (data['model'] if item['id'] in ['screening','extraction'] else 'deterministic'))),(T['decision-context'],URIRef('urn:sha256:'+data['cases_sha256'])),(A.parameters,Literal(json.dumps({'sample_size':s['selected'],'seed':s['seed']}),datatype=RDF.JSON)),(T['selected-result'],result)]:g.add((node,p,o))
  fields={A.status:item['status'],A.partial:s['partial'],A.populationCount:s['population'],A.selectedCount:s['selected'],A.evaluatedCount:s['evaluated'],A.inconclusiveCount:s['inconclusive'],A.samplingMethod:s['method'],A.samplingSeed:s['seed'],A.metricNumerator:m['numerator'],A.limitations:item['limitations']}
  g.add((result,RDF.type,A.AuditResult))
  for p,v in fields.items():g.add((result,p,Literal(v)))
  if m['agreement'] is not None:g.add((result,A.agreement,Literal(Decimal(str(m['agreement'])),datatype=XSD.decimal)))
  g.add((result,A.resultArtifact,URIRef('urn:sha256:'+hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest())))
 return g
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('--revision',required=True);p.add_argument('--graph',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 g=convert(json.loads(a.results.read_text()),a.revision,a.graph);ok,_,report=validate(g,shacl_graph=str(Path(__file__).parent/'schemas/audit.ttl'));assert ok,report;g.serialize(destination=a.output,format='turtle');print(report)

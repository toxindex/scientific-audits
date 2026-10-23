import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audits import sample,receipt,db_check
from results_rdf import convert
from pyshacl import validate
class Tests(unittest.TestCase):
 def test_sampling_is_order_independent(self):
  rows=[{'id':str(i)} for i in range(10)]
  self.assertEqual(sample(rows,3,'s'),sample(rows[::-1],3,'s'))
 def test_inconclusive_is_not_agreement(self):
  r=receipt('x','x',[{'verdict':'agree'},{'verdict':'inconclusive'}],10,2)
  self.assertEqual(r['metrics']['denominator'],1);self.assertTrue(r['sampling']['partial'])
 def test_database_bad_key_fails(self):
  r=db_check({'id':'x','provenance':{'rows':[{'alias':'r','table':'t','primaryKey':[{'column':'id','valueJson':'1'}]}],'cells':[{'table':'t','columnRef':'r.id','valueJson':'2'}]}})
  self.assertEqual(r['verdict'],'disagree')
 def test_missing_context_does_not_pass(self):
  self.assertEqual(receipt('x','x',[],0,0)['status'],'not-assessable')
 def test_shacl(self):
  r=receipt('x','x',[{'verdict':'agree'}],2,1)
  data={'graph_sha256':'a'*64,'cases_sha256':'b'*64,'model':'test','audits':[r]}
  g=convert(data,'c'*40,'urn:test:graph');ok,_,report=validate(g,shacl_graph=str(Path(__file__).resolve().parents[1]/'schemas/audit.ttl'));self.assertTrue(ok,report)
if __name__=='__main__':unittest.main()

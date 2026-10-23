import sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from linkml_check import run
SCHEMA='''id: urn:test:schema
name: example
prefixes:
  test: 'urn:test:'
  linkml: https://w3id.org/linkml/
imports:
  - linkml:types
default_prefix: test
classes:
  Person:
    attributes:
      name:
        range: string
        required: true
      category:
        range: Category
      age:
        range: integer
        minimum_value: 0
enums:
  Category:
    permissible_values:
      person:
'''
class Tests(unittest.TestCase):
 def evaluate(self,ttl):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'schema.yaml').write_text(SCHEMA);(p/'g.ttl').write_text('@prefix t: <urn:test:> . '+ttl)
   return run(p/'g.ttl',[p/'schema.yaml'],p/'out',full=True)
 def test_valid_entity_and_blank_node(self):
  r=self.evaluate('t:a a t:Person; t:name "A"; t:age 1; t:category "person" . [] a t:Person; t:name "B" .')
  self.assertEqual(r['status'],'pass');self.assertEqual(r['counts']['entities'],2)
 def test_untyped_and_unknown(self):
  r=self.evaluate('t:a t:name "A" . t:b a t:NotDeclared .')
  self.assertEqual(r['status'],'fail');self.assertEqual(r['counts']['untyped_entities'],1);self.assertEqual(r['counts']['unknown_type_assertions'],1)
 def test_required_range_and_minimum(self):
  r=self.evaluate('t:a a t:Person; t:age -2 . t:b a t:Person; t:name "B"; t:age "bad" .')
  self.assertEqual(r['status'],'fail');self.assertGreaterEqual(r['counts']['constraint_violations'],3)
if __name__=='__main__':unittest.main()

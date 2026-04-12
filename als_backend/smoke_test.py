import urllib.request, json

# Test /health
r = urllib.request.urlopen("http://localhost:8000/health")
print("Health:", json.loads(r.read()))

# Test /api/graph
r = urllib.request.urlopen("http://localhost:8000/api/graph?student_id=test_student_01")
data = json.loads(r.read())
print(f"\nGraph endpoint OK - Nodes: {len(data['nodes'])}, Links: {len(data['links'])}")
for n in data["nodes"]:
    print(f"  {n['id']:20} mastery={n['mastery']:5.1f}  conf={n['confidence']:5.1f}  decay={n['decay']:.4f}")

# Test /api/next-question
r = urllib.request.urlopen("http://localhost:8000/api/next-question?student_id=test_student_01")
q = json.loads(r.read())
print(f"\nFirst Question ({q['questionType']}) about [{q['targetConcept']}]:")
print(f"  {q['nextQuestion'][:120]}...")

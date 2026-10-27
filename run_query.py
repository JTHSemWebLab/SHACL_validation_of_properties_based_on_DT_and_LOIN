#################################################################
# IMPORTS
#################################################################

from pathlib import Path
from rdflib import Graph

#################################################################
# ONTOLOGY RESOURCES
#################################################################

g = Graph()

folder = Path(r"C:/Testfiler/new_test")

files = [
    "SETemplate.ttl",
    "SETemplatewindowresources.ttl",
    "requirements.ttl",
    "shapes.ttl",
    "framematerialscheme.ttl",
    "tempo.ttl",
    "loin.ttl",
]

for filename in files:
    filepath = folder / filename

    with filepath.open("r", encoding="utf-8") as f:
        g.parse(file=f, format="turtle")

print(f"Loaded {len(g)} triples.")

# Prefixes
PREFIXES = """
PREFIX req:     <http://example.org/requirements/>
PREFIX loin:    <https://w3id.org/loin#>
PREFIX setemp:  <https://example.org/setemp#>
PREFIX setempw: <https://example.org/setempw#>
PREFIX tempo:   <https://w3id.org/tempo#>
PREFIX sh:      <http://www.w3.org/ns/shacl#>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX framematerial: <https://example.org/framematerialscheme#>
PREFIX qudt:    <http://qudt.org/schema/qudt/>
"""

#################################################################
# QUERY DEFINITIONS
#################################################################

# Q1
query1 = PREFIXES + """
SELECT DISTINCT ?property ?label
WHERE {
    ?template tempo:isAssignedToObjectType setempw:Window ;
              tempo:hasProperty ?property .

    OPTIONAL {
        ?property rdfs:label ?label .
    }
}
"""

# Q2
query2 = PREFIXES + """
SELECT ?shape
WHERE {
    req:WindowLOIN_DetailDesign
        loin:hasAlphanumericalInformation ?shape .

    ?shape a sh:NodeShape .
}
"""

# Q3
query3 = PREFIXES + """
SELECT ?valueType
WHERE {
    req:WindowLOIN_DetailDesign
        loin:hasAlphanumericalInformation ?shape .

    ?shape
        a sh:NodeShape ;
        sh:property ?propertyShape .

    ?propertyShape
        sh:path setempw:Frame_Height ;
        sh:node ?valueConstraint .

    ?valueConstraint
        sh:class ?valueType .
}
"""

# Q4
query4 = PREFIXES + """
SELECT ?frameMaterial ?notation
WHERE {
    setempw:Frame_Material
        setemp:expectsScheme ?scheme .

    ?frameMaterial
        a skos:Concept ;
        skos:inScheme ?scheme ;
        skos:notation ?notation .
}
"""

# Q5
query5 = PREFIXES + """
SELECT DISTINCT ?property ?label
WHERE {
    setempw:WindowTemplate
        tempo:hasProperty ?property .

    req:WindowLOIN_DetailDesign
        loin:hasAlphanumericalInformation ?shape .

    ?shape
        a sh:NodeShape ;
        sh:property ?propertyShape .

    ?propertyShape
        sh:path ?property .

    OPTIONAL {
        ?property rdfs:label ?label .
    }
}
"""

#################################################################
# RUN QUERIES
#################################################################

# Run query function
def run_query(graph, query, title):
    print(f"\n{title}")
    print("-" * len(title))

    results = graph.query(query)

    for row in results:
        print(" | ".join(str(value) for value in row))


# Run queries
run_query(
    g,
    query1,
    "CQ1: Which properties are included in the window template?"
)

run_query(
    g,
    query2,
    "CQ2: Which shapes belong to WindowLOIN_DetailDesign?"
)

run_query(
    g,
    query3,
    "CQ3: What is the expected value type of frame height?"
)

run_query(
    g,
    query4,
    "CQ4: Which controlled values are available for frame material?"
)

run_query(
    g,
    query5,
    "CQ5: Which window template properties are required by WindowLOIN_DetailDesign?"
)
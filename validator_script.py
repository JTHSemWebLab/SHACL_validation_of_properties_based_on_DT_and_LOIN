#################################################################
# IMPORTS
#################################################################

from rdflib import Graph, Namespace, RDF, BNode
from pyshacl import validate
from openpyxl import Workbook
import logging
import csv
from rdflib.namespace import SKOS


#################################################################
# LOADING ONTOLOGIES & REQUIREMENT SET
#################################################################

# Turn off pyshacl debug verbosity unless you want it
logging.getLogger("pyshacl").setLevel(logging.WARNING)

# Namespaces
LOIN = Namespace("https://w3id.org/loin#")
REQ = Namespace("http://example.org/requirements/")
SHAPES = Namespace("http://example.org/shapes/")
SH = Namespace("http://www.w3.org/ns/shacl#")
SETEMP = Namespace("https://example.org/setemp#")

# Load ontologies + shapes + requirements + data
g = Graph()
g.parse(r"C:/Testfiler/new_test\SETemplate.ttl", format="turtle")
g.parse(r"C:/Testfiler/new_test/loin.ttl", format="turtle")
g.parse(r"C:/Testfiler/new_test/tempo.ttl", format="turtle")
g.parse(r"C:/Testfiler/new_test\SETemplatewindowresources.ttl", format="turtle")
shapes = Graph().parse(r"C:/Testfiler/new_test\shapes.ttl", format="turtle")
requirements = Graph().parse(r"C:/Testfiler/new_test/requirements.ttl", format="turtle")
data = Graph().parse(r"C:/Testfiler/new_test\data.ttl", format="turtle")
selected_shapes = Graph().parse(r"C:/Testfiler/new_test/selected_shapes.ttl")



#################################################################
# MAP REQUIRED SKOS SCHEMES
#################################################################

properties = set()

for shape in selected_shapes.subjects(RDF.type, SH.NodeShape):
    for prop_shape in selected_shapes.objects(shape, SH.property):
        for path in selected_shapes.objects(prop_shape, SH.path):
            properties.add(path)

schemes = set()
discrete_numeric_props = set()

for prop in properties:
    # SKOS schemes
    for scheme in g.objects(prop, SETEMP.expectsScheme):
        schemes.add(scheme)
    # Discrete numeric constraints
    for _ in g.objects(prop, SETEMP.allowedNumbers):
        discrete_numeric_props.add(prop)

# DEBUG
print("Properties found:")
for p in properties:
    print(" -", p)
print("Schemes found:")
for s in schemes:
    print(" -", s)
print("Schemes (raw IRIs):")
for s in schemes:
    print(repr(str(s)))

SCHEME_GRAPH_MAP = {
    "https://example.org/framematerialscheme#FrameMaterialScheme": r"C:/Testfiler/new_test/framematerialscheme.ttl",
    "https://example.org/windowtypescheme#WindowTypeScheme": r"C:/Testfiler/new_test/windowtypescheme.ttl",
    "https://example.org/burglarresistancescheme#BurglarResistanceScheme": r"C:/Testfiler/new_test/burglarresistancescheme.ttl",
    "https://example.org/jambextensionscheme#JambExtensionScheme": r"C:/Testfiler/new_test/jambextensionscheme.ttl",
    "https://example.org/openingdirectionscheme#OpeningDirectionScheme": r"C:/Testfiler/new_test/openingdirectionscheme.ttl",
    "https://example.org/rotationaldirectionscheme#RotationalDirectionScheme": r"C:/Testfiler/new_test/rotationaldirectionscheme.ttl",
    "https://example.org/fireresistancescheme#FireResistanceScheme": r"C:/Testfiler/new_test/fireresistancescheme.ttl",
    # add more schemes here
}

vocab_graph = Graph()

for scheme in schemes:
    scheme_str = str(scheme)
    if scheme_str in SCHEME_GRAPH_MAP:
        vocab_graph.parse(SCHEME_GRAPH_MAP[scheme_str], format="turtle")
    else:
        print(f"WARNING: No graph mapping for scheme {scheme_str}")

data_graph = data + g + vocab_graph


#################################################################
# SHACL VALIDATION
#################################################################

# Validate using the selected_shapes graph
conforms, results_graph, results_text = validate(
    data_graph=data_graph,
    shacl_graph=selected_shapes,
    data_graph_format="turtle",
    shacl_graph_format="turtle",
    inference="rdfs",
    debug=False  # set True only when debugging
)

SH = Namespace("http://www.w3.org/ns/shacl#")

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Validation terminal message:
violations = list(results_graph.subjects(RDF.type, SH.ValidationResult))

if conforms:
    print(f"{GREEN}{BOLD}✅ Conforms: True — no violations!{RESET}")
else:
    print(f"{RED}{BOLD}❌ Conforms: False — {len(violations)} violation(s) found:{RESET}\n")
    for i, result in enumerate(violations, start=1):
        focus = results_graph.value(result, SH.focusNode)
        path = results_graph.value(result, SH.resultPath)
        value = results_graph.value(result, SH.value)
        message = results_graph.value(result, SH.resultMessage)
        
        # Compact single-line per violation
        print(
            f"{YELLOW}[{i}]{RESET} "
            f"{BOLD}Focus:{RESET} {focus} | "
            f"{BOLD}Path:{RESET} {path} | "
            f"{BOLD}Value:{RESET} {value} | "
            f"{BOLD}Message:{RESET} {message}"
        )


#################################################################
# VALIDATION RESULTS TO CSV
#################################################################

violations = []
for result in results_graph.subjects(RDF.type, SH.ValidationResult):
    r = {
        "focus_node": results_graph.value(result, SH.focusNode),
        "path": results_graph.value(result, SH.resultPath),
        "value": results_graph.value(result, SH.value),
        "message": results_graph.value(result, SH.resultMessage),
        "source_shape": results_graph.value(result, SH.sourceShape)
    }
    violations.append(r)

if violations:
    with open("validation_results.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=violations[0].keys())
        writer.writeheader()
        for row in violations:
            # convert rdflib terms to strings
            writer.writerow({k: str(v) if v is not None else "" for k, v in row.items()})
    print("CSV report saved to validation_results.csv")
else:
    print("No violations found!")
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

# Load ontologies + shapes + requirements
g = Graph()
g.parse(r"C:/Testfiler/new_test\SETemplate.ttl", format="turtle")
g.parse(r"C:/Testfiler/new_test/loin.ttl", format="turtle")
g.parse(r"C:/Testfiler/new_test/tempo.ttl", format="turtle")
g.parse(r"C:/Testfiler/new_test\SETemplatewindowresources.ttl", format="turtle")
shapes = Graph().parse(r"C:/Testfiler/new_test\shapes.ttl", format="turtle")
requirements = Graph().parse(r"C:/Testfiler/new_test/requirements.ttl", format="turtle")


# Pick which requirement set we are validating against
current_loin = REQ["WindowLOIN_DetailDesign"]


#################################################################
# FUNCTION DEFINITIONS
#################################################################

# Recursively copy all triples about a node (including RDF list nodes) into g_dst.
def copy_deep(g_src, g_dst, node, visited=None):

    if visited is None:
        visited = set()
    if node in visited:
        return
    visited.add(node)

    for p, o in g_src.predicate_objects(node):
        g_dst.add((node, p, o))
        if isinstance(o, BNode):
            copy_deep(g_src, g_dst, o, visited)
        if p == RDF.rest and o != RDF.nil:
            copy_deep(g_src, g_dst, o, visited)


# Get values for excel export
def get_allowed_values(prop_shape, selected_shapes, vocab_graph, ontology_graph):
    values = set()

    # 1. SHACL sh:in (explicit lists)
    for inlist in selected_shapes.objects(prop_shape, SH["in"]):
        try:
            members = list(selected_shapes.items(inlist))
            values.update(str(x) for x in members)
        except Exception:
            values.add(str(inlist))

    # 2. SKOS schemes (dynamic controlled vocabularies)
    # Case A: flattened
    for inner_prop in selected_shapes.objects(prop_shape, SH.property):
        for scheme in selected_shapes.objects(inner_prop, SH.hasValue):
            for concept in vocab_graph.subjects(SKOS.inScheme, scheme):
                label = next(vocab_graph.objects(concept, SKOS.prefLabel), None)
                values.add(str(label) if label else str(concept))

    # Case B: nested
    for node_shape in selected_shapes.objects(prop_shape, SH.node):
        for inner_prop in selected_shapes.objects(node_shape, SH.property):
            for scheme in selected_shapes.objects(inner_prop, SH.hasValue):
                for concept in vocab_graph.subjects(SKOS.inScheme, scheme):
                    label = next(vocab_graph.objects(concept, SKOS.prefLabel), None)
                    values.add(str(label) if label else str(concept))

    # 3. Discrete numeric values (ontology-driven)
    for path in selected_shapes.objects(prop_shape, SH.path):
        for num_list in ontology_graph.objects(path, SETEMP.allowedNumbers):
            try:
                members = list(ontology_graph.items(num_list))
                values.update(str(x) for x in members)
            except Exception:
                values.add(str(num_list))

    return sorted(values)


#################################################################
# CONSTRUCT GRAPH WITH ONLY REQUIRED SHAPES
#################################################################

selected_shapes = Graph()

# Debug: print triples for the selected requirement set to confirm predicate used
print("Triples for the selected requirement set:")
for s, p, o in requirements.triples((current_loin, None, None)):
    print("  ", p, "->", o)

# Adjust predicate according to what's actually in requirements.ttl
predicate_for_shapes = LOIN.hasAlphanumericalInformation

# Collect shapes referenced by the requirement set
referenced_shapes = list(requirements.objects(current_loin, predicate_for_shapes))
print("Referenced shapes (raw):", referenced_shapes)

# Copy deep each referenced shape into selected_shapes
for shape in referenced_shapes:
    copy_deep(shapes, selected_shapes, shape)

# Debug: print how many node shapes we have in selected_shapes
node_shapes = set(selected_shapes.subjects(RDF.type, SH.NodeShape))
print("Number of NodeShapes in selected_shapes:", len(node_shapes))
for ns in node_shapes:
    print(" -", ns)

# If no node shapes were found, also try to detect shapes declared in shapes graph and warn
if not node_shapes:
    print("WARNING: No sh:NodeShape found in the selected_shapes graph. Inspect shapes.ttl and requirements.ttl.")


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


#################################################################
# REUQIREMENTS TO EXCEL
#################################################################

# Prepare Excel workbook
wb = Workbook()
ws = wb.active
ws.title = "Requirements"
ws.append(["Shape", "Target Class", "Property", "Datatype", "MinCount", "MaxCount", "Allowed Values"])

# Iterate over node shapes extracted from selected_shapes
for shape in sorted(node_shapes, key=lambda x: str(x)):
    # Target class
    target_class = next(selected_shapes.objects(shape, SH.targetClass), None)

    # Property shapes
    for prop_shape in selected_shapes.objects(shape, SH.property):
        path = next(selected_shapes.objects(prop_shape, SH.path), None)
        datatype = next(selected_shapes.objects(prop_shape, SH.datatype), None)
        min_count = next(selected_shapes.objects(prop_shape, SH.minCount), None)
        max_count = next(selected_shapes.objects(prop_shape, SH.maxCount), None)

        allowed_values = get_allowed_values(
            prop_shape,
            selected_shapes,
            vocab_graph,
            g
        )
        allowed_values_str = ", ".join(allowed_values)

        ws.append([
            str(shape),
            str(target_class) if target_class else "",
            str(path) if path else "",
            str(datatype) if datatype else "",
            str(min_count) if min_count else "",
            str(max_count) if max_count else "",
            allowed_values_str
        ])

# Save requirements to Excel file for user to read
outfile = "requirements_checklist.xlsx"
wb.save(outfile)
print("Excel checklist written:", outfile)

# Serialize selected_shapes to a .ttl-file
selected_shapes.serialize(destination="selected_shapes.ttl", format="turtle")
print("Selected shapes serialized to selected_shapes.ttl for inspection.")


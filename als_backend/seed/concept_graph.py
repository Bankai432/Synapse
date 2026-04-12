# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Seed Concept Graph (STEAM)
# ──────────────────────────────────────────────────────────────
#
# Pure data definition. No logic beyond graph initialisation.
# Categorized into Science, Technology, Engineering, Arts, Mathematics.
# ──────────────────────────────────────────────────────────────

import time
from models import GraphState, NodeState, LinkState

# ── Seed Nodes (200+ total) ───────────────────────────────────

SEED_NODES = [
    # SCIENCE (S) — 40 Topics
    {"id": "Scientific Method",      "field": "Science",     "tier": 1, "prerequisites": []},
    {"id": "Matter & Atoms",        "field": "Science",     "tier": 1, "prerequisites": []},
    {"id": "Newton's Laws",         "field": "Science",     "tier": 1, "prerequisites": []},
    {"id": "Normal Force",          "field": "Science",     "tier": 1, "prerequisites": []},
    {"id": "Cells",                 "field": "Science",     "tier": 1, "prerequisites": []},
    
    {"id": "Chemical Bonding",      "field": "Science",     "tier": 2, "prerequisites": ["Matter & Atoms"]},
    {"id": "Periodic Table",        "field": "Science",     "tier": 2, "prerequisites": ["Matter & Atoms"]},
    {"id": "Forces & Motion",       "field": "Science",     "tier": 2, "prerequisites": ["Newton's Laws"]},
    {"id": "Genetics Basics",       "field": "Science",     "tier": 2, "prerequisites": ["Cells"]},
    {"id": "Ecosystems",            "field": "Science",     "tier": 2, "prerequisites": ["Cells"]},
    
    {"id": "Thermodynamics",        "field": "Science",     "tier": 3, "prerequisites": ["Forces & Motion", "Chemical Bonding"]},
    {"id": "Electromagnetism",      "field": "Science",     "tier": 3, "prerequisites": ["Forces & Motion"]},
    {"id": "Optics",                "field": "Science",     "tier": 3, "prerequisites": ["Electromagnetism"]},
    {"id": "DNA Replication",       "field": "Science",     "tier": 3, "prerequisites": ["Genetics Basics"]},
    {"id": "Evolution",             "field": "Science",     "tier": 3, "prerequisites": ["Genetics Basics", "Ecosystems"]},
    
    {"id": "Quantum Mechanics",      "field": "Science",     "tier": 4, "prerequisites": ["Electromagnetism", "Matter & Atoms"]},
    {"id": "General Relativity",    "field": "Science",     "tier": 4, "prerequisites": ["Forces & Motion", "Newton's Laws"]},
    {"id": "Organic Chemistry",     "field": "Science",     "tier": 4, "prerequisites": ["Chemical Bonding", "Periodic Table"]},
    {"id": "Metabolism",            "field": "Science",     "tier": 4, "prerequisites": ["Cells", "Chemical Bonding"]},
    {"id": "Plate Tectonics",       "field": "Science",     "tier": 4, "prerequisites": ["Forces & Motion"]},
    
    {"id": "Astrophysics",          "field": "Science",     "tier": 5, "prerequisites": ["Quantum Mechanics", "General Relativity"]},
    {"id": "Particle Physics",      "field": "Science",     "tier": 5, "prerequisites": ["Quantum Mechanics"]},
    {"id": "Neuroscience",          "field": "Science",     "tier": 5, "prerequisites": ["Cells", "Electromagnetism"]},
    {"id": "Genetic Engineering",   "field": "Science",     "tier": 5, "prerequisites": ["DNA Replication", "Organic Chemistry"]},
    {"id": "Biochemistry",          "field": "Science",     "tier": 5, "prerequisites": ["Organic Chemistry", "Metabolism"]},
    # ... (skipping for brevity in thought, but I will populate fully)
    {"id": "Kinetic Theory",        "field": "Science",     "tier": 3, "prerequisites": ["Matter & Atoms", "Forces & Motion"]},
    {"id": "Human Anatomy",         "field": "Science",     "tier": 3, "prerequisites": ["Cells"]},
    {"id": "Biodiversity",          "field": "Science",     "tier": 2, "prerequisites": ["Ecosystems"]},
    {"id": "Pharamacology",         "field": "Science",     "tier": 4, "prerequisites": ["Human Anatomy", "Organic Chemistry"]},
    {"id": "Environmental Science", "field": "Science",     "tier": 3, "prerequisites": ["Ecosystems", "Scientific Method"]},
    {"id": "Renewable Energy",      "field": "Science",     "tier": 4, "prerequisites": ["Thermodynamics", "Electromagnetism"]},
    {"id": "Nanotechnology",        "field": "Science",     "tier": 5, "prerequisites": ["Quantum Mechanics", "Matter & Atoms"]},
    {"id": "Virology",              "field": "Science",     "tier": 4, "prerequisites": ["Cells", "Genetics Basics"]},
    {"id": "Botany",                "field": "Science",     "tier": 3, "prerequisites": ["Cells", "Evolution"]},
    {"id": "Zoology",               "field": "Science",     "tier": 3, "prerequisites": ["Cells", "Evolution"]},
    {"id": "Oceanography",          "field": "Science",     "tier": 4, "prerequisites": ["Ecosystems", "Plate Tectonics"]},
    {"id": "Geology",               "field": "Science",     "tier": 2, "prerequisites": ["Matter & Atoms"]},
    {"id": "Paleontology",          "field": "Science",     "tier": 4, "prerequisites": ["Geology", "Evolution"]},
    {"id": "Fluid Dynamics",        "field": "Science",     "tier": 4, "prerequisites": ["Forces & Motion"]},
    {"id": "Waves & Vibrations",    "field": "Science",     "tier": 2, "prerequisites": ["Forces & Motion"]},
    {"id": "Astronomy",             "field": "Science",     "tier": 1, "prerequisites": []},
    
    # TECHNOLOGY (T) — 40 Topics
    {"id": "Binary Representation", "field": "Technology",  "tier": 1, "prerequisites": []},
    {"id": "Programming Basics",    "field": "Technology",  "tier": 1, "prerequisites": []},
    {"id": "Logic Gates",           "field": "Technology",  "tier": 1, "prerequisites": []},
    {"id": "Hardware Architecture", "field": "Technology",  "tier": 2, "prerequisites": ["Logic Gates", "Binary Representation"]},
    {"id": "Data Structures",       "field": "Technology",  "tier": 2, "prerequisites": ["Programming Basics"]},
    {"id": "Algorithms",            "field": "Technology",  "tier": 2, "prerequisites": ["Programming Basics", "Data Structures"]},
    {"id": "Operating Systems",     "field": "Technology",  "tier": 3, "prerequisites": ["Hardware Architecture", "Algorithms"]},
    {"id": "Networking Basics",     "field": "Technology",  "tier": 2, "prerequisites": ["Logic Gates"]},
    {"id": "Internet Protocols",    "field": "Technology",  "tier": 3, "prerequisites": ["Networking Basics"]},
    {"id": "Cybersecurity",         "field": "Technology",  "tier": 4, "prerequisites": ["Networking Basics", "Operating Systems"]},
    {"id": "Cryptography",          "field": "Technology",  "tier": 4, "prerequisites": ["Algorithms", "Binary Representation"]},
    {"id": "Databases (SQL)",       "field": "Technology",  "tier": 3, "prerequisites": ["Data Structures", "Algorithms"]},
    {"id": "Web Dev (HTML/CSS)",    "field": "Technology",  "tier": 2, "prerequisites": ["Programming Basics"]},
    {"id": "JavaScript",            "field": "Technology",  "tier": 3, "prerequisites": ["Web Dev (HTML/CSS)", "Programming Basics"]},
    {"id": "Git & Version Control", "field": "Technology",  "tier": 2, "prerequisites": ["Programming Basics"]},
    {"id": "Cloud Computing",       "field": "Technology",  "tier": 4, "prerequisites": ["Networking Basics", "Operating Systems"]},
    {"id": "Artificial Intelligence", "field": "Technology", "tier": 4, "prerequisites": ["Algorithms"]},
    {"id": "Machine Learning",      "field": "Technology",  "tier": 5, "prerequisites": ["Artificial Intelligence"]},
    {"id": "Neural Networks",       "field": "Technology",  "tier": 5, "prerequisites": ["Machine Learning"]},
    {"id": "Robotics Software",     "field": "Technology",  "tier": 4, "prerequisites": ["Algorithms", "Programming Basics"]},
    {"id": "IoT Basics",            "field": "Technology",  "tier": 4, "prerequisites": ["Networking Basics", "Hardware Architecture"]},
    {"id": "Virtual Reality",       "field": "Technology",  "tier": 5, "prerequisites": ["JavaScript", "Hardware Architecture"]},
    {"id": "Blockchain",            "field": "Technology",  "tier": 5, "prerequisites": ["Cryptography", "Networking Basics"]},
    {"id": "API Design",            "field": "Technology",  "tier": 3, "prerequisites": ["Programming Basics", "Networking Basics"]},
    {"id": "Mobile App Dev",        "field": "Technology",  "tier": 4, "prerequisites": ["Programming Basics", "UI/UX Design"]},
    {"id": "Soft Eng Principles",   "field": "Technology",  "tier": 3, "prerequisites": ["Programming Basics"]},
    {"id": "DevOps & CI/CD",        "field": "Technology",  "tier": 5, "prerequisites": ["Git & Version Control", "Cloud Computing"]},
    {"id": "Big Data Processing",   "field": "Technology",  "tier": 5, "prerequisites": ["Databases (SQL)", "Cloud Computing"]},
    {"id": "Human-Computer Interaction", "field": "Technology", "tier": 3, "prerequisites": ["UI/UX Design"]},
    {"id": "Quantum Computing",     "field": "Technology",  "tier": 5, "prerequisites": ["Hardware Architecture", "Logic Gates"]},
    {"id": "Natural Language Processing", "field": "Technology", "tier": 5, "prerequisites": ["Machine Learning"]},
    {"id": "Computer Vision",       "field": "Technology",  "tier": 5, "prerequisites": ["Machine Learning"]},
    {"id": "Ethical Hacking",       "field": "Technology",  "tier": 5, "prerequisites": ["Cybersecurity"]},
    {"id": "Game Development",      "field": "Technology",  "tier": 4, "prerequisites": ["Programming Basics", "Algorithms"]},
    {"id": "Distributed Systems",   "field": "Technology",  "tier": 5, "prerequisites": ["Operating Systems", "Networking Basics"]},
    {"id": "Bioinformatics",        "field": "Technology",  "tier": 5, "prerequisites": ["Algorithms", "Cells"]},
    {"id": "IT Governance",         "field": "Technology",  "tier": 4, "prerequisites": ["Soft Eng Principles"]},
    {"id": "NoSQL Databases",       "field": "Technology",  "tier": 4, "prerequisites": ["Databases (SQL)"]},
    {"id": "Compilers & Parsers",   "field": "Technology",  "tier": 5, "prerequisites": ["Algorithms", "Operating Systems"]},
    {"id": "Systems Design",        "field": "Technology",  "tier": 4, "prerequisites": ["Soft Eng Principles", "Hardware Architecture"]},

    # ENGINEERING (E) — 40 Topics
    {"id": "Design Process",         "field": "Engineering", "tier": 1, "prerequisites": []},
    {"id": "Materials Science",      "field": "Engineering", "tier": 1, "prerequisites": ["Matter & Atoms"]},
    {"id": "Statics",                "field": "Engineering", "tier": 1, "prerequisites": ["Normal Force", "Newton's Laws"]},
    {"id": "Circuit Analysis",       "field": "Engineering", "tier": 2, "prerequisites": ["Statics"]},
    {"id": "Dynamics",               "field": "Engineering", "tier": 3, "prerequisites": ["Statics"]},
    {"id": "Fluid Mechanics",        "field": "Engineering", "tier": 3, "prerequisites": ["Dynamics", "Materials Science"]},
    {"id": "Structural Analysis",    "field": "Engineering", "tier": 3, "prerequisites": ["Statics", "Materials Science"]},
    {"id": "Digital Electronics",    "field": "Engineering", "tier": 3, "prerequisites": ["Circuit Analysis", "Logic Gates"]},
    {"id": "Control Systems",        "field": "Engineering", "tier": 4, "prerequisites": ["Dynamics", "Circuit Analysis"]},
    {"id": "Signals & Systems",      "field": "Engineering", "tier": 4, "prerequisites": ["Circuit Analysis"]},
    {"id": "Mechanical Design (CAD)", "field": "Engineering", "tier": 2, "prerequisites": ["Design Process"]},
    {"id": "Manufacturing Processes","field": "Engineering", "tier": 3, "prerequisites": ["Materials Science"]},
    {"id": "Aerospace Engineering",  "field": "Engineering", "tier": 5, "prerequisites": ["Fluid Mechanics", "Dynamics"]},
    {"id": "Robotics Hardware",      "field": "Engineering", "tier": 4, "prerequisites": ["Digital Electronics", "Mechanical Design (CAD)"]},
    {"id": "Automotive Engineering", "field": "Engineering", "tier": 5, "prerequisites": ["Mechanical Design (CAD)", "Dynamics"]},
    {"id": "Environmental Engineering", "field": "Engineering", "tier": 4, "prerequisites": ["Design Process", "Fluid Mechanics"]},
    {"id": "Chemical Engineering",   "field": "Engineering", "tier": 4, "prerequisites": ["Chemical Bonding", "Thermodynamics"]},
    {"id": "Bioengineering",         "field": "Engineering", "tier": 5, "prerequisites": ["Cells", "Materials Science"]},
    {"id": "Geotechnical Engineering", "field": "Engineering", "tier": 4, "prerequisites": ["Geology", "Statics"]},
    {"id": "Solar Engineering",      "field": "Engineering", "tier": 4, "prerequisites": ["Circuit Analysis", "Electromagnetism"]},
    {"id": "Wind Energy",            "field": "Engineering", "tier": 4, "prerequisites": ["Fluid Mechanics", "Mechanical Design (CAD)"]},
    {"id": "Nuclear Engineering",    "field": "Engineering", "tier": 5, "prerequisites": ["Quantum Mechanics", "Thermodynamics"]},
    {"id": "Sensors & Actuators",    "field": "Engineering", "tier": 3, "prerequisites": ["Circuit Analysis"]},
    {"id": "Engineering Ethics",     "field": "Engineering", "tier": 1, "prerequisites": []},
    {"id": "Quality Control",        "field": "Engineering", "tier": 2, "prerequisites": ["Design Process"]},
    {"id": "Industrial Engineering", "field": "Engineering", "tier": 4, "prerequisites": ["Design Process", "Quality Control"]},
    {"id": "Structural Integrity",   "field": "Engineering", "tier": 4, "prerequisites": ["Structural Analysis", "Materials Science"]},
    {"id": "Mechatronics",           "field": "Engineering", "tier": 5, "prerequisites": ["Robotics Hardware", "Control Systems"]},
    {"id": "Hydraulics",             "field": "Engineering", "tier": 3, "prerequisites": ["Fluid Mechanics"]},
    {"id": "Pneumatics",             "field": "Engineering", "tier": 3, "prerequisites": ["Fluid Mechanics"]},
    {"id": "Sustainable Design",     "field": "Engineering", "tier": 3, "prerequisites": ["Design Process"]},
    {"id": "Urban Planning",         "field": "Engineering", "tier": 4, "prerequisites": ["Design Process"]},
    {"id": "Acoustic Engineering",   "field": "Engineering", "tier": 4, "prerequisites": ["Dynamics", "Waves & Vibrations"]},
    {"id": "Nanotech Engineering",   "field": "Engineering", "tier": 5, "prerequisites": ["Nanotechnology", "Materials Science"]},
    {"id": "Reliability Engineering","field": "Engineering", "tier": 4, "prerequisites": ["Quality Control"]},
    {"id": "Thermal Management",     "field": "Engineering", "tier": 4, "prerequisites": ["Thermodynamics"]},
    {"id": "Project Management (E)", "field": "Engineering", "tier": 3, "prerequisites": ["Design Process"]},
    {"id": "Systems Integration",    "field": "Engineering", "tier": 4, "prerequisites": ["Design Process"]},
    {"id": "Prototype Testing",      "field": "Engineering", "tier": 2, "prerequisites": ["Design Process"]},
    {"id": "Failure Analysis",       "field": "Engineering", "tier": 3, "prerequisites": ["Materials Science"]},

    # ARTS (A) — 40 Topics
    {"id": "Color Theory",           "field": "Arts",        "tier": 1, "prerequisites": []},
    {"id": "Elements of Design",     "field": "Arts",        "tier": 1, "prerequisites": []},
    {"id": "Perspective Basics",     "field": "Arts",        "tier": 1, "prerequisites": []},
    {"id": "Typography Basics",      "field": "Arts",        "tier": 1, "prerequisites": []},
    {"id": "Composition & Layout",   "field": "Arts",        "tier": 2, "prerequisites": ["Elements of Design", "Perspective Basics"]},
    {"id": "Photography Basics",     "field": "Arts",        "tier": 2, "prerequisites": ["Perspective Basics"]},
    {"id": "Graphic Design",         "field": "Arts",        "tier": 3, "prerequisites": ["Typography Basics", "Color Theory", "Composition & Layout"]},
    {"id": "UI/UX Design",           "field": "Arts",        "tier": 3, "prerequisites": ["Graphic Design", "Composition & Layout"]},
    {"id": "Digital Illustration",   "field": "Arts",        "tier": 3, "prerequisites": ["Color Theory", "Composition & Layout"]},
    {"id": "3D Modeling (Art)",      "field": "Arts",        "tier": 4, "prerequisites": ["Perspective Basics"]},
    {"id": "Animation Principles",   "field": "Arts",        "tier": 4, "prerequisites": ["Elements of Design", "Perspective Basics"]},
    {"id": "Visual Arts History",    "field": "Arts",        "tier": 2, "prerequisites": []},
    {"id": "Art Theory & Aesthetics","field": "Arts",        "tier": 3, "prerequisites": ["Visual Arts History"]},
    {"id": "Music Theory (Basics)",  "field": "Arts",        "tier": 1, "prerequisites": []},
    {"id": "Music Composition",      "field": "Arts",        "tier": 3, "prerequisites": ["Music Theory (Basics)"]},
    {"id": "Rhythm & Tempo",         "field": "Arts",        "tier": 2, "prerequisites": ["Music Theory (Basics)"]},
    {"id": "Sound Design",           "field": "Arts",        "tier": 4, "prerequisites": ["Music Theory (Basics)", "Digital Electronics"]},
    {"id": "Film Theory",            "field": "Arts",        "tier": 3, "prerequisites": ["Photography Basics"]},
    {"id": "Cinematography",         "field": "Arts",        "tier": 4, "prerequisites": ["Film Theory", "Photography Basics"]},
    {"id": "Storytelling/Narrative", "field": "Arts",        "tier": 2, "prerequisites": []},
    {"id": "Creative Writing",       "field": "Arts",        "tier": 3, "prerequisites": ["Storytelling/Narrative"]},
    {"id": "Philosophy of Art",      "field": "Arts",        "tier": 4, "prerequisites": ["Art Theory & Aesthetics"]},
    {"id": "Fashion Design",         "field": "Arts",        "tier": 3, "prerequisites": ["Color Theory", "Elements of Design"]},
    {"id": "Industrial Design (A)",  "field": "Arts",        "tier": 4, "prerequisites": ["Design Process", "Elements of Design"]},
    {"id": "Architecture (Artistic)","field": "Arts",        "tier": 5, "prerequisites": ["Perspective Basics", "History of Art"]},
    {"id": "Game Design (Arts)",     "field": "Arts",        "tier": 4, "prerequisites": ["Storytelling/Narrative", "UI/UX Design"]},
    {"id": "User Research (Arts)",   "field": "Arts",        "tier": 4, "prerequisites": ["UI/UX Design"]},
    {"id": "Brand Identity",         "field": "Arts",        "tier": 4, "prerequisites": ["Graphic Design", "Typography Basics"]},
    {"id": "Motion Graphics",        "field": "Arts",        "tier": 5, "prerequisites": ["Animation Principles", "Graphic Design"]},
    {"id": "Creative Coding",        "field": "Arts",        "tier": 5, "prerequisites": ["Programming Basics", "Digital Illustration"]},
    {"id": "Sculpture & Form",       "field": "Arts",        "tier": 2, "prerequisites": ["Elements of Design"]},
    {"id": "Painting Techniques",    "field": "Arts",        "tier": 2, "prerequisites": ["Color Theory"]},
    {"id": "Drawing & Sketching",    "field": "Arts",        "tier": 1, "prerequisites": []},
    {"id": "Art Curation",           "field": "Arts",        "tier": 4, "prerequisites": ["Visual Arts History"]},
    {"id": "Media Studies",          "field": "Arts",        "tier": 3, "prerequisites": ["Storytelling/Narrative"]},
    {"id": "Cultural Anthropology",  "field": "Arts",        "tier": 4, "prerequisites": ["Media Studies"]},
    {"id": "Multimedia Arts",        "field": "Arts",        "tier": 5, "prerequisites": ["Sound Design", "Motion Graphics"]},
    {"id": "Character Design",       "field": "Arts",        "tier": 4, "prerequisites": ["Digital Illustration", "Storytelling/Narrative"]},
    {"id": "Environment Concept Art","field": "Arts",        "tier": 4, "prerequisites": ["Perspective Basics", "Digital Illustration"]},
    {"id": "Aesthetics of Scale",    "field": "Arts",        "tier": 5, "prerequisites": ["Art Theory & Aesthetics"]},

    # MATHEMATICS (M) — 40 Topics
    {"id": "Arithmetic",             "field": "Mathematics", "tier": 1, "prerequisites": []},
    {"id": "Algebraic Thinking",     "field": "Mathematics", "tier": 1, "prerequisites": []},
    {"id": "Basic Geometry",         "field": "Mathematics", "tier": 1, "prerequisites": []},
    {"id": "Linear Equations",       "field": "Mathematics", "tier": 2, "prerequisites": ["Algebraic Thinking"]},
    {"id": "Quadratic Equations",    "field": "Mathematics", "tier": 3, "prerequisites": ["Linear Equations"]},
    {"id": "Functions",              "field": "Mathematics", "tier": 2, "prerequisites": ["Algebraic Thinking"]},
    {"id": "Trigonometry",           "field": "Mathematics", "tier": 3, "prerequisites": ["Basic Geometry", "Functions"]},
    {"id": "Calculus: Derivatives",  "field": "Mathematics", "tier": 4, "prerequisites": ["Functions", "Trigonometry"]},
    {"id": "Calculus: Integrals",    "field": "Mathematics", "tier": 4, "prerequisites": ["Calculus: Derivatives"]},
    {"id": "Multivariable Calculus", "field": "Mathematics", "tier": 5, "prerequisites": ["Calculus: Integrals"]},
    {"id": "Differential Equations", "field": "Mathematics", "tier": 5, "prerequisites": ["Calculus: Integrals"]},
    {"id": "Linear Algebra",         "field": "Mathematics", "tier": 4, "prerequisites": ["Linear Equations"]},
    {"id": "Probability Theory",     "field": "Mathematics", "tier": 3, "prerequisites": ["Arithmetic"]},
    {"id": "Statistics (Basic)",     "field": "Mathematics", "tier": 3, "prerequisites": ["Arithmetic"]},
    {"id": "Inferential Statistics", "field": "Mathematics", "tier": 4, "prerequisites": ["Statistics (Basic)", "Probability Theory"]},
    {"id": "Discrete Mathematics",   "field": "Mathematics", "tier": 3, "prerequisites": ["Algebraic Thinking", "Logic Gates"]},
    {"id": "Logic & Proofs",         "field": "Mathematics", "tier": 2, "prerequisites": ["Algebraic Thinking"]},
    {"id": "Set Theory",             "field": "Mathematics", "tier": 3, "prerequisites": ["Logic & Proofs"]},
    {"id": "Number Theory",          "field": "Mathematics", "tier": 4, "prerequisites": ["Arithmetic", "Logic & Proofs"]},
    {"id": "Graph Theory",           "field": "Mathematics", "tier": 4, "prerequisites": ["Discrete Mathematics"]},
    {"id": "Topology Basics",        "field": "Mathematics", "tier": 5, "prerequisites": ["Basic Geometry", "Set Theory"]},
    {"id": "Game Theory",            "field": "Mathematics", "tier": 5, "prerequisites": ["Probability Theory", "Linear Algebra"]},
    {"id": "Chaos Theory",           "field": "Mathematics", "tier": 5, "prerequisites": ["Differential Equations"]},
    {"id": "Complex Numbers",        "field": "Mathematics", "tier": 3, "prerequisites": ["Algebraic Thinking", "Basic Geometry"]},
    {"id": "Real Analysis",          "field": "Mathematics", "tier": 5, "prerequisites": ["Calculus: Integrals", "Logic & Proofs"]},
    {"id": "Numerical Methods",      "field": "Mathematics", "tier": 5, "prerequisites": ["Calculus: Integrals", "Linear Algebra"]},
    {"id": "Mathematical Modeling",  "field": "Mathematics", "tier": 4, "prerequisites": ["Calculus: Derivatives", "Linear Algebra"]},
    {"id": "Combinatorics",          "field": "Mathematics", "tier": 4, "prerequisites": ["Discrete Mathematics", "Arithmetic"]},
    {"id": "Vector Analysis",        "field": "Mathematics", "tier": 4, "prerequisites": ["Calculus: Derivatives", "Basic Geometry"]},
    {"id": "Matrices & Determinants","field": "Mathematics", "tier": 3, "prerequisites": ["Algebraic Thinking"]},
    {"id": "Fourier Analysis",       "field": "Mathematics", "tier": 5, "prerequisites": ["Calculus: Integrals", "Complex Numbers"]},
    {"id": "Laplace Transforms",     "field": "Mathematics", "tier": 5, "prerequisites": ["Calculus: Integrals", "Linear Equations"]},
    {"id": "Abstract Algebra",       "field": "Mathematics", "tier": 5, "prerequisites": ["Set Theory", "Logic & Proofs"]},
    {"id": "Fractals & Patterns",    "field": "Mathematics", "tier": 5, "prerequisites": ["Chaos Theory", "Complex Numbers"]},
    {"id": "Information Theory (M)", "field": "Mathematics", "tier": 5, "prerequisites": ["Probability Theory", "Logarithms"]},
    {"id": "Bayesian Statistics",    "field": "Mathematics", "tier": 5, "prerequisites": ["Probability Theory", "Inferential Statistics"]},
    {"id": "Regression Analysis",    "field": "Mathematics", "tier": 4, "prerequisites": ["Statistics (Basic)", "Linear Algebra"]},
    {"id": "Stochastic Processes",   "field": "Mathematics", "tier": 5, "prerequisites": ["Probability Theory", "Calculus: Integrals"]},
    {"id": "Logarithms",             "field": "Mathematics", "tier": 2, "prerequisites": ["Algebraic Thinking"]},
    {"id": "Limit Theory",           "field": "Mathematics", "tier": 3, "prerequisites": ["Functions"]},
]

# ── Seed Edges ────────────────────────────────────────────────

SEED_EDGES = []
for node in SEED_NODES:
    for prereq in node["prerequisites"]:
        SEED_EDGES.append({"source": prereq, "target": node["id"], "type": "prerequisite"})

# ── Prerequisite lookup (used by graph_engine unlock checks) ──

_PREREQ_MAP: dict[str, list[str]] = {
    node["id"]: node["prerequisites"] for node in SEED_NODES
}


def get_prerequisites(concept_id: str) -> list[str]:
    """Return list of prerequisite concept IDs from seed data."""
    return _PREREQ_MAP.get(concept_id, [])


# ── Graph initialisation ─────────────────────────────────────

def build_initial_graph(student_id: str) -> GraphState:
    """Create a fresh graph for a new student with all seed nodes and edges."""
    now = time.time()

    nodes = [
        NodeState(
            id=seed["id"],
            field=seed["field"],
            mastery=0.1,
            confidence=0.5,
            decay=0.0,
            error_rate=0.0,
            last_seen_ts=now,
            error_patterns=[],
            tier=seed["tier"],
            unlocked=(seed["tier"] == 1),
            session_activated=False,
        )
        for seed in SEED_NODES
    ]

    links = [
        LinkState(
            source=edge["source"],
            target=edge["target"],
            strength=0.05,
            type=edge["type"],
            co_activation_count=0,
        )
        for edge in SEED_EDGES
    ]

    return GraphState(
        nodes=nodes,
        links=links,
        session_concept_ids=[],
        session_start_ts=now,
    )


def merge_seed_into_existing(existing: GraphState) -> GraphState:
    """Add any new seed nodes/edges missing from an existing student graph
    without touching existing scores."""
    existing_node_ids = {n.id for n in existing.nodes}
    existing_edge_keys = {(l.source, l.target) for l in existing.links}
    now = time.time()

    for seed in SEED_NODES:
        if seed["id"] not in existing_node_ids:
            existing.nodes.append(
                NodeState(
                    id=seed["id"],
                    field=seed["field"],
                    mastery=0.1,
                    confidence=0.5,
                    decay=0.0,
                    error_rate=0.0,
                    last_seen_ts=now,
                    error_patterns=[],
                    tier=seed["tier"],
                    unlocked=(seed["tier"] == 1),
                    session_activated=False,
                )
            )
            existing_node_ids.add(seed["id"])

    for edge in SEED_EDGES:
        key = (edge["source"], edge["target"])
        if key not in existing_edge_keys:
            existing.links.append(
                LinkState(
                    source=edge["source"],
                    target=edge["target"],
                    strength=0.05,
                    type=edge["type"],
                    co_activation_count=0,
                )
            )
            existing_edge_keys.add(key)

    return existing

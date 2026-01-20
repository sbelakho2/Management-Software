#!/usr/bin/env python3
"""
Filter out irrelevant books from the downloaded collection.
Removes dictionaries, novels, religious texts, encyclopedias, and other
content not related to TPS/Lean/manufacturing/business/management.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Set

# Directories
TXT_DIR = Path("txt")
CLEANED_DIR = Path("cleaned")
FILTERED_OUT_DIR = Path("filtered_out")  # Move irrelevant files here instead of deleting

# Keywords that indicate IRRELEVANT content (fiction, reference books, religious texts)
IRRELEVANT_PATTERNS = [
    # Dictionaries and encyclopedias (all languages)
    r'\bdictionary\b', r'\bdiccionario\b', r'\bdictionnaire\b', r'\bwörterbuch\b',
    r'\bdizionario\b', r'\bwoordenboek\b', r'\bsłownik\b', r'\bordbok\b',
    r'\bencyclopedia\b', r'\benciclopedia\b', r'\bencyclopédie\b', r'\benzyklopädie\b',
    r'\blexicon\b', r'\bléxico\b', r'\bglossary\b', r'\bglosario\b',
    r'\bthesaurus\b', r'\btesauro\b',
    
    # Religious texts (all languages)
    r'\bbible\b', r'\bbiblia\b', r'\bbibel\b', r'\bbiblical\b',
    r'\bquran\b', r'\bkoran\b', r'\bcorán\b', r'\balcorán\b',
    r'\btorah\b', r'\btalmud\b', r'\bvedas?\b', r'\bbhagavad\b',
    r'\bpsalms?\b', r'\bsalmos?\b', r'\bgospel\b', r'\bevangelio\b',
    r'\bgenesis\b', r'\bexodus\b', r'\bleviticus\b', r'\bdeuteronomy\b',
    r'\brevelation\b', r'\bapocalipsis\b', r'\bapocalypse\b',
    r'\bsermon\b', r'\bsermón\b', r'\bpredigt\b',
    r'\bhymn\b', r'\bhimno\b', r'\bcatechism\b', r'\bcatecismo\b',
    r'\bprayer\b', r'\boración\b', r'\bgebet\b', r'\bprière\b',
    r'\bsaints?\b', r'\bsantos?\b', r'\bheiligen\b',
    r'\bchristian\b', r'\bcristiano\b', r'\bmuslim\b', r'\bislámic\b',
    r'\bjesus\b', r'\bjesús\b', r'\bchrist\b', r'\bcristo\b',
    r'\bmoses\b', r'\bmoisés\b', r'\bprophet\b', r'\bprofeta\b',
    r'\bgreat controversy\b',  # Religious book
    
    # Classic literature and novels (titles in multiple languages)
    r'\bwar and peace\b', r'\bguerra y paz\b', r'\bguerre et paix\b',
    r'\bles trois mousquetaires\b', r'\bthree musketeers\b', r'\btres mosqueteros\b',
    r'\bdivina com+edia\b', r'\bdivine comedy\b', r'\bgöttliche komödie\b',
    r'\bdon quixote\b', r'\bdon quijote\b',
    r'\boliver twist\b', r'\bwuthering heights\b', r'\bcumbres borrascosas\b',
    r'\bjane eyre\b', r'\bpride and prejudice\b', r'\borgullo y prejuicio\b',
    r'\bgreat expectations\b', r'\bgrandes esperanzas\b',
    r'\bmoby dick\b', r'\bthe odyssey\b', r'\bodisea\b', r'\bὀδύσσεια\b',
    r'\biliad\b', r'\bilíada\b', r'\bἰλιάς\b',
    r'\baeneid\b', r'\beneida\b',
    r'\bbeowulf\b', r'\bcanterbury tales\b',
    r'\bparadise lost\b', r'\bparaíso perdido\b',
    r'\bfaust\b', r'\bfausto\b',
    r'\bles misérables\b', r'\blos miserables\b',
    r'\banna karenina\b',
    r'\bbrothers karamazov\b', r'\bhermanos karamázov\b',
    r'\bcrime and punishment\b', r'\bcrimen y castigo\b',
    r'\bfrankenstein\b', r'\bdracula\b', r'\bdrácula\b',
    r'\bsherlock holmes\b',
    r'\bportrait of a lady\b', r'\bretrato de una dama\b',
    r'\broughing it\b',
    r'\banne of green gables\b',
    r'\bpollyanna\b',
    r'\bblack cat\b', r'\bgato negro\b',
    r'\bballad of reading gaol\b',
    r'\bthe alhambra\b',
    r'\bles liaisons dangereuses\b', r'\brelaciones peligrosas\b',
    r'\bchartreuse de parme\b',
    r'\bmoriæ encomium\b', r'\bpraise of folly\b', r'\belogio de la locura\b',
    r'\bfables\b', r'\bfábulas\b',
    r'\bdon juan tenorio\b',
    r'\brichest man in babylon\b',  # Self-help, not manufacturing
    r'\bway to wealth\b',
    r'\bsaint.{0,3}s? everlasting rest\b',
    r'\bautobiography\b', r'\bautobiografía\b',
    r'\bhistory of england\b', r'\bhistoria de inglaterra\b',
    r'\bsurvey of london\b',
    r'\btour.*whole island.*britain\b',
    r'\bhistory.*donner party\b',
    r'\bessay concerning human understanding\b',
    r'\bπολιτεία\b',  # Plato's Republic in Greek
    r'\bθεαίτητος\b',  # Theaetetus in Greek
    
    # Poetry collections
    r'\bpoesías\b', r'\bpoems?\b', r'\bpoemas?\b', r'\bgedichte\b',
    r'\bpoésie\b', r'\bsonnet\b', r'\bsoneto\b',
    r'\bballad\b', r'\bbalada\b',
    r'\bleyenda en verso\b',
    
    # Plays and theater (not business-related)
    r'\bcomedia en\b', r'\bzarzuela\b', r'\bjuguete cómico\b',
    r'\bpasillo cómico\b', r'\btragedia\b', r'\bteatro\b',
    
    # Navigation/maritime (not manufacturing-focused)
    r'\bpractical navigator\b', r'\bnavegante práctico\b',
    
    # Historical/genealogical (not manufacturing)
    r'\bhistoria genealogica\b', r'\bgenealogical history\b',
    r'\banales históricos de la medicina\b',
    r'\bhistory of the.*administration\b',
    r'\bhistoria de.*administracion\b(?!.*lean|.*kaizen|.*mejora)',
    
    # Government/legal codes (not manufacturing)
    r'\bcódigo.*leyes\b', r'\bcódigos postal\b', r'\bcódigo telegráfico\b',
    r'\bconsejo de administracion\b(?!.*lean|.*kaizen)',
    r'\bdecretos?\b(?!.*lean|.*manufacturing)',
    
    # Newspapers and periodicals (unless specifically about lean/manufacturing)
    r'\btelegraph\b(?!.*lean)', r'\bnewspaper\b(?!.*kaizen|.*lean)',
    r'\bperiódico\b(?!.*kaizen|.*lean)',
    
    # Military history (unless about lean logistics)
    r'\bbatallas?\b', r'\bcampaña\b(?!.*lean|.*mejora)',
    r'\boperaciones.*ejército\b', r'\bmilitary.*history\b',
    r'\btrial of\b', r'\bjuicio de\b',
    
    # Medical (unless about lean healthcare)
    r'\bbreast cancer\b', r'\bcáncer\b(?!.*lean|.*six sigma)',
    
    # Weather/climate (unless about manufacturing)
    r'\bweatherman\b', r'\bwind blows\b',
    
    # Random fiction indicators
    r'\bnovel\b', r'\bnovela\b', r'\broman\b',
    r'\bfiction\b', r'\bficción\b',
    r'\bshort stor(y|ies)\b', r'\bcuento\b',
    r'\bfairy tale\b', r'\bcuento de hadas\b',
    
    # Cookbooks and recipes
    r'\brecipes?\b', r'\brecetas?\b', r'\bcookbook\b',
    
    # Hiroshima (historical, not manufacturing)
    r'\bhiroshima\b(?!.*lean|.*manufacturing)',
    
    # Investment/personal finance books (not manufacturing)
    r'\binvesting in\b(?!.*manufacturing|.*lean)',
    
    # Index files
    r'\bindex\b$', r'\bíndice\b$',
    r'vol\s*\d+\s*index',
]

# Keywords that indicate RELEVANT content (keep these!)
RELEVANT_PATTERNS = [
    # TPS/Lean/Kaizen
    r'\btps\b', r'\btoyota\b', r'\blean\b', r'\bkaizen\b', r'\bkanban\b',
    r'\bjidoka\b', r'\bheijunka\b', r'\bpoka.?yoke\b', r'\bandon\b',
    r'\bmuda\b', r'\bmuri\b', r'\bmura\b', r'\bgemba\b', r'\bgenchi genbutsu\b',
    r'\b5s\b', r'\bsix sigma\b', r'\b6σ\b', r'\bseis sigma\b',
    r'\bvalue stream\b', r'\bflujo de valor\b',
    r'\bcontinuous improvement\b', r'\bmejora continua\b',
    r'\bprocess improvement\b', r'\bmejora de procesos\b',
    
    # Manufacturing
    r'\bmanufacturing\b', r'\bmanufactura\b', r'\bfabricación\b',
    r'\bproduction\b', r'\bproducción\b', r'\bproduktion\b',
    r'\bfactory\b', r'\bfábrica\b', r'\bplant\b', r'\bplanta\b',
    r'\bassembly\b', r'\bmontaje\b', r'\bensamblaje\b',
    r'\bquality control\b', r'\bcontrol de calidad\b',
    r'\bquality management\b', r'\bgestión de calidad\b',
    r'\btotal quality\b', r'\bcalidad total\b',
    r'\biso 9001\b', r'\biso 14001\b',
    
    # Supply chain and logistics
    r'\bsupply chain\b', r'\bcadena de suministro\b',
    r'\blogistics\b', r'\blogística\b',
    r'\binventory\b', r'\binventario\b',
    r'\bwarehouse\b', r'\balmacén\b',
    r'\bprocurement\b', r'\badquisición\b',
    
    # Operations and management
    r'\boperations management\b', r'\bgestión de operaciones\b',
    r'\bproject management\b', r'\bgestión de proyectos\b',
    r'\bworkforce\b', r'\bfuerza laboral\b',
    r'\bproductivity\b', r'\bproductividad\b',
    r'\befficiency\b', r'\beficiencia\b',
    r'\boptimization\b', r'\boptimización\b',
    r'\bstandardization\b', r'\bestandarización\b',
    
    # Agile/software engineering (relevant to modern operations)
    r'\bagile\b', r'\bágil\b', r'\bscrum\b', r'\bsprint\b',
    r'\bdevops\b', r'\bcmmi\b',
    
    # Defense/aerospace manufacturing
    r'\bdtic\b', r'\bdarpa\b', r'\bnasa\b',
    r'\baerospace\b', r'\baeroespacial\b',
    r'\bdefense\b', r'\bdefensa\b',
    r'\bacquisition\b', r'\badquisición\b',
    
    # Business process
    r'\bbusiness process\b', r'\bproceso de negocio\b',
    r'\breengineering\b', r'\breingeniería\b',
    r'\bworkflow\b', r'\bflujo de trabajo\b',
    
    # Maintenance
    r'\bmaintenance\b', r'\bmantenimiento\b',
    r'\bdepot\b', r'\breparación\b',
    
    # Training/education in manufacturing context
    r'\btraining.*manufactur\b', r'\bcapacitación.*manufactura\b',
    r'\bworkplace.*training\b',
    
    # Specific relevant topics
    r'\bsustainment\b', r'\bsostenibilidad\b',
    r'\baudit\b', r'\bauditoría\b',
    r'\bcost.*reduction\b', r'\breducción.*costos\b',
    r'\bwaste.*reduction\b', r'\breducción.*desperdicios\b',
    r'\bcycle time\b', r'\btiempo de ciclo\b',
    r'\blead time\b',
    r'\bthroughput\b', r'\brendimiento\b',
]


def compile_patterns(patterns: list) -> list:
    """Compile regex patterns for faster matching."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def is_relevant(filename: str, content: str = "") -> tuple[bool, str]:
    """
    Determine if a file is relevant to TPS/Lean/manufacturing.
    Returns (is_relevant, reason).
    """
    text_to_check = filename.lower()
    
    # If we have content, check first ~5000 chars for relevance
    if content:
        text_to_check += " " + content[:5000].lower()
    
    # First check if it contains ANY relevant keywords
    relevant_found = []
    for pattern in compile_patterns(RELEVANT_PATTERNS):
        if pattern.search(text_to_check):
            relevant_found.append(pattern.pattern)
    
    # Check for irrelevant patterns
    irrelevant_found = []
    for pattern in compile_patterns(IRRELEVANT_PATTERNS):
        if pattern.search(text_to_check):
            irrelevant_found.append(pattern.pattern)
    
    # Decision logic:
    # 1. If it has relevant keywords, keep it (even if it has some irrelevant markers)
    if relevant_found:
        return True, f"Relevant: {', '.join(relevant_found[:3])}"
    
    # 2. If it has irrelevant keywords and no relevant ones, filter it out
    if irrelevant_found:
        return False, f"Irrelevant: {', '.join(irrelevant_found[:3])}"
    
    # 3. If neither, keep it (might be relevant content with different terminology)
    return True, "No strong indicators - keeping by default"


def filter_books():
    """Filter out irrelevant books from the collection."""
    
    # Create filtered_out directory
    FILTERED_OUT_DIR.mkdir(exist_ok=True)
    
    # Process both txt and cleaned directories
    directories = [TXT_DIR, CLEANED_DIR]
    
    stats = {
        'kept': 0,
        'filtered': 0,
        'errors': 0,
    }
    
    filtered_files = []
    kept_files = []
    
    for directory in directories:
        if not directory.exists():
            continue
            
        print(f"\n{'='*60}")
        print(f"Processing: {directory}")
        print(f"{'='*60}")
        
        for filepath in sorted(directory.glob("*.txt")):
            try:
                # Read first part of file for content analysis
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10000)  # Read first 10KB
                except:
                    content = ""
                
                is_rel, reason = is_relevant(filepath.name, content)
                
                if is_rel:
                    stats['kept'] += 1
                    kept_files.append((filepath.name, reason))
                    print(f"✓ KEEP: {filepath.name[:60]}...")
                else:
                    stats['filtered'] += 1
                    filtered_files.append((filepath.name, reason))
                    
                    # Move to filtered_out directory
                    dest = FILTERED_OUT_DIR / f"{directory.name}_{filepath.name}"
                    shutil.move(str(filepath), str(dest))
                    print(f"✗ FILTER: {filepath.name[:50]}... -> {reason}")
                    
            except Exception as e:
                stats['errors'] += 1
                print(f"ERROR processing {filepath.name}: {e}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("FILTERING COMPLETE")
    print(f"{'='*60}")
    print(f"Files kept: {stats['kept']}")
    print(f"Files filtered out: {stats['filtered']}")
    print(f"Errors: {stats['errors']}")
    
    if filtered_files:
        print(f"\n--- Filtered files moved to: {FILTERED_OUT_DIR} ---")
        print("\nFiltered files by reason:")
        reasons = {}
        for name, reason in filtered_files:
            key = reason.split(':')[0] if ':' in reason else reason
            if key not in reasons:
                reasons[key] = []
            reasons[key].append(name)
        
        for reason, files in reasons.items():
            print(f"\n{reason}: {len(files)} files")
            for f in files[:5]:  # Show first 5
                print(f"  - {f[:70]}...")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
    
    return stats


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    filter_books()

"""NBCRNA content outline (effective 2024-01-02): four domains and lettered sections.

These labels are sourced from the user's 12-page NBCRNA NCE outline.
Only domain weights are official; no subdomain weights are implied.
"""
from board_item_quality import BLUEPRINTS, blueprint_counts

SECTIONS = {
 "basic_sciences": {
  "A": "Anatomy and physiology", "B": "Pathophysiology",
  "C": "Pharmacology", "D": "Applied chemistry, biochemistry, physics, and mathematics"},
 "equipment_instrumentation_technology": {
  "A": "Anesthetic delivery systems", "B": "Airway equipment",
  "C": "Monitoring devices", "D": "Patient warming equipment",
  "E": "Infusion devices", "F": "Imaging and imaging safety"},
 "general_principles_of_anesthesia": {
  "A": "Ethical considerations", "B": "Legal issues", "C": "Safety and wellness",
  "D": "Preoperative assessment and preparation of patient",
  "E": "Fluid volume assessment and management", "F": "Positioning",
  "G": "Utilization and interpretation of testing data", "H": "Airway management",
  "I": "Local/regional anesthetics", "J": "Light, moderate, and deep sedation",
  "K": "Total intravenous anesthesia", "L": "Pain",
  "M": "Enhanced recovery after surgery", "N": "Hypotensive technique and risks",
  "O": "Postanesthesia care/respiratory therapy", "P": "Infection control",
  "Q": "Intraoperative fire safety"},
 "surgical_procedures_special_populations": {
  "A": "Surgical and diagnostic anesthesia, including management of complications",
  "B": "Anesthesia for special populations"},
}

# Objective labels mirror the numbered outline headings. They are not quotas.
OBJECTIVES = {
 "basic_sciences": {
  "A": ["Cardiovascular", "Respiratory", "Central nervous system", "Musculoskeletal",
        "Endocrine", "Hepatic and renal", "Hematologic", "Gastrointestinal", "Immune"],
  "B": ["Cardiovascular", "Respiratory", "Central nervous system", "Musculoskeletal",
        "Endocrine", "Hepatic", "Renal", "Hematologic", "Gastrointestinal", "Immune",
        "Other conditions"],
  "C": ["General principles", "Inhalation anesthetics", "Intravenous anesthetics and antagonists",
        "Depolarizing and nondepolarizing neuromuscular relaxants and antagonists",
        "Local anesthetics", "Lipid emulsion", "Regional anesthesia adjuncts",
        "Anticholinergics/cholinergic agonists", "Non-opioid analgesics",
        "Cardiovascular medications", "Bronchodilators", "Psychopharmacologic therapy",
        "Prostaglandins", "Histamine receptor antagonists", "Antiemetics", "Insulin",
        "Hypoglycemics", "Diuretics", "Anticoagulants and antagonists", "Procoagulants",
        "Antimicrobials and antivirals", "Antiepileptics", "Lipid-lowering agents",
        "Herbal remedies and dietary supplements", "Minerals and electrolytes",
        "Dantrolene", "Steroids", "Tocolytics", "Uterotonics", "Intravenous dyes",
        "Cannabinoids"],
  "D": ["Chemistry and biochemistry", "Physics", "Nonpharmacology-related mathematics"]},
 "equipment_instrumentation_technology": {
  "A": ["High/low pressure gas sources", "Regulators/manifolds", "Flowmeters, valves, floats",
        "Vaporizers", "Proportioning systems", "Pressure failure safety devices",
        "Failsafe devices", "Ventilator", "Carbon dioxide absorbents", "Anesthetic circuits",
        "Pneumatic and electronic alarm devices"],
  "B": ["Face masks", "Laryngoscope", "Flexible fiberoptic bronchoscope",
        "Endotracheal tube", "Endobronchial tube", "Airways", "Tracheostomy tubes",
        "Supraglottic airways", "Intubating supraglottic airways", "Jet ventilation",
        "Intubating stylets", "Cricothyrotomy", "Intubation aids"],
  "C": ["Central nervous system", "Cardiovascular", "Respiratory", "Others"],
  "D": ["Fluid/blood warmers", "Forced air warming devices",
        "Heat and moisture exchanger", "Radiant warmers"],
  "E": ["Infusion devices"],
  "F": ["Ultrasound", "Fluoroscopy", "Radiography"]},
 "general_principles_of_anesthesia": {
  "E": ["Fluid/blood component therapy replacement", "Bloodless medicine",
        "Goal-directed fluid management", "Massive transfusion protocol", "Thromboelastography"],
  "F": ["Techniques", "Physiologic alterations", "Complications"],
  "G": ["Lab tests", "Diagnostic exams"],
  "H": ["Assessment", "Techniques, procedures, and devices", "Complications",
        "Difficult airway management"],
  "I": ["Anatomy", "Infiltration", "Topical", "Neuraxial blocks", "Peripheral blocks",
        "Other blocks", "Ultrasound and/or nerve stimulator guided concepts and techniques",
        "Management of complications"],
  "L": ["Pain theory", "Pain management"],
  "P": ["Provider", "Patient"]},
 "surgical_procedures_special_populations": {
  "A": ["Intra-abdominal", "Extrathoracic", "Head", "Cardiac anesthesia",
        "Noncardiac intrathoracic", "Neck", "Neuroskeletal", "Orthopedic",
        "Perineal and pelvic procedures", "Vascular", "Non-operating-room anesthesia",
        "Robotic/laparoscopic surgery", "Other surgical procedures"],
  "B": ["Pediatrics", "Obstetrics", "Geriatrics", "Obesity",
        "Substance use disorder population", "Immune compromised and oncology patients"]},
}


def validate_classification(domain, section=None, objective=None):
    if domain not in SECTIONS:
        return False
    if section is None:
        return objective is None
    if section not in SECTIONS[domain]:
        return False
    return objective is None or objective in OBJECTIVES.get(domain, {}).get(section, [])


def exam_blueprint(mode, total):
    if mode not in BLUEPRINTS:
        raise ValueError("Mode must be NCE or SEE")
    return {"mode": mode, "domain_counts": blueprint_counts(total, BLUEPRINTS[mode]),
            "subdomain_weights_official": False}


def coverage(items, mode="NCE"):
    """Report classification coverage without inventing subdomain quotas."""
    if mode not in BLUEPRINTS:
        raise ValueError("Invalid mode")
    result = {domain: {"total": 0, "sections": {key: 0 for key in sections}}
              for domain, sections in SECTIONS.items()}
    unclassified = 0
    for item in items:
        domain, section = item.get("nceDomain"), item.get("nceSection")
        if not validate_classification(domain, section, item.get("nceObjective")) or section is None:
            unclassified += 1
            continue
        result[domain]["total"] += 1
        result[domain]["sections"][section] += 1
    return {"mode": mode, "domains": result, "unclassified": unclassified,
            "official_domain_weights": BLUEPRINTS[mode]}

import json

with open("frontend/src/locales/en.json") as f:
    d = json.load(f)

p = d.setdefault("pages", {}).setdefault("executive", {})

# ops section
p.setdefault("ops", {})
p["ops"]["activeUsers"] = "Active Users"
p["ops"]["openWorkOrders"] = "Open Work Orders"
p["ops"]["productionEfficiency"] = "Production Efficiency"
p["ops"]["pendingApprovals"] = "Pending Approvals"

# sqdcp pillar labels
p.setdefault("sqdcp", {})
p["sqdcp"]["safety"] = "Safety"
p["sqdcp"]["quality"] = "Quality"
p["sqdcp"]["delivery"] = "Delivery"
p["sqdcp"]["cost"] = "Cost"
p["sqdcp"]["people"] = "People"

# KPI score card labels
p["kpi"]["qualityScore"] = "Quality Score"
p["kpi"]["deliveryScore"] = "Delivery Score"
p["kpi"]["costEfficiency"] = "Cost Efficiency"
p["kpi"]["workforce"] = "Workforce"
p["kpi"]["overallScore"] = "Overall Score"
p["kpi"]["belowTarget"] = "Below Target"
p["kpi"]["awaitingData"] = "Awaiting Data"

# Tour / onboarding keys
d.setdefault("tour", {})
d["tour"]["back"] = "Back"
d["tour"]["next"] = "Next"
d["tour"]["finish"] = "Finish"
d["tour"]["closeTour"] = "Close tour"
d["tour"]["productTour"] = "Product tour"
d["tour"]["stepOf"] = "{current} of {total}"

# GRR results chart keys
d.setdefault("quality", {}).setdefault("grr", {})
g = d["quality"]["grr"]
g["analysisResults"] = "GRR Analysis Results"
g["gauge"] = "Gauge: {name}"
g["totalGageRR"] = "Total Gage R&R"
g["excellent"] = "Excellent"
g["acceptable"] = "Acceptable"
g["unacceptable"] = "Unacceptable"
g["msgExcellent"] = "Measurement system is acceptable"
g["msgAcceptable"] = "May be acceptable depending on application"
g["msgUnacceptable"] = "Measurement system needs improvement"
g["variationBreakdown"] = "Variation Breakdown"
g["variationTooltip"] = "Shows the contribution of each source to total variation. Lower EV+AV (GRR) means better measurement system."
g["equipmentVariation"] = "Equipment Variation (EV): {value}%"
g["repeatability"] = "Repeatability"
g["appraiserVariation"] = "Appraiser Variation (AV): {value}%"
g["reproducibility"] = "Reproducibility"
g["partVariationPct"] = "Part Variation (PV): {value}%"
g["actualPartVariation"] = "Actual part-to-part variation"
g["legendEV"] = "EV (Repeatability)"
g["legendAV"] = "AV (Reproducibility)"
g["legendPV"] = "PV (Part Variation)"
g["repeatabilityEV"] = "Repeatability (EV)"
g["reproducibilityAV"] = "Reproducibility (AV)"
g["partVariation"] = "Part Variation (PV)"
g["totalVariation"] = "Total Variation (TV)"
g["ndcTitle"] = "Number of Distinct Categories (NDC)"
g["ndcAcceptable"] = "≥ 5 (Acceptable)"
g["ndcNeedsImprovement"] = "< 5 (Needs Improvement)"
g["ndcDescription"] = "NDC represents how many distinct part categories the measurement system can reliably distinguish. AIAG recommends a minimum of 5 distinct categories."
g["aiagGuidelines"] = "AIAG MSA Guidelines:"
g["aiagExcellent"] = "< 10% GRR: Measurement system is acceptable"
g["aiagAcceptable"] = "10-30% GRR: May be acceptable based on application importance"
g["aiagUnacceptable"] = "> 30% GRR: Measurement system needs improvement"

with open("frontend/src/locales/en.json", "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("Done - added all missing keys")

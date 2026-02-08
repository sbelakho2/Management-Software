#!/usr/bin/env python3
"""Add missing i18n keys to en.json for HR, maintenance, and expand existing sections."""
import json

with open("frontend/src/locales/en.json") as f:
    d = json.load(f)

# Add HR section
d["hr"] = {
    "title": "Human Resources",
    "employees": {
        "title": "Employees",
        "addEmployee": "Add Employee",
        "editEmployee": "Edit Employee",
        "firstName": "First Name",
        "lastName": "Last Name",
        "email": "Email",
        "department": "Department",
        "position": "Position",
        "status": "Status",
        "active": "Active",
        "inactive": "Inactive",
        "onLeave": "On Leave",
        "hireDate": "Hire Date",
        "searchPlaceholder": "Search employees...",
        "noEmployees": "No employees found",
        "createSuccess": "Employee created successfully",
        "updateSuccess": "Employee updated successfully",
        "deleteSuccess": "Employee removed successfully",
        "deleteConfirm": "Are you sure you want to delete this employee?",
        "requiredField": "This field is required",
        "invalidEmail": "Please enter a valid email address",
    },
    "jobOpenings": {
        "title": "Job Openings",
        "addOpening": "Add Job Opening",
        "jobTitle": "Job Title",
        "department": "Department",
        "location": "Location",
        "type": "Employment Type",
        "status": "Status",
        "open": "Open",
        "closed": "Closed",
        "filled": "Filled",
        "postedDate": "Posted Date",
        "closingDate": "Closing Date",
        "applications": "Applications",
        "noOpenings": "No job openings",
    },
    "leaveRequests": {
        "title": "Leave Requests",
        "addRequest": "New Leave Request",
        "employee": "Employee",
        "leaveType": "Leave Type",
        "startDate": "Start Date",
        "endDate": "End Date",
        "status": "Status",
        "pending": "Pending",
        "approved": "Approved",
        "rejected": "Rejected",
        "reason": "Reason",
        "noRequests": "No leave requests",
        "approve": "Approve",
        "reject": "Reject",
    },
    "applicationsPipeline": {
        "title": "Applications Pipeline",
        "applied": "Applied",
        "screening": "Screening",
        "interview": "Interview",
        "offered": "Offered",
        "hired": "Hired",
    },
    "tabs": {
        "employees": "Employees",
        "jobOpenings": "Job Openings",
        "leaveRequests": "Leave Requests",
        "applicationsPipeline": "Applications Pipeline",
    },
    "toasts": {
        "employeeCreated": "Employee created successfully",
        "employeeUpdated": "Employee updated successfully",
        "leaveApproved": "Leave request approved",
        "leaveRejected": "Leave request rejected",
        "openingCreated": "Job opening created",
    },
}

# Add maintenance section
d["maintenance"] = {
    "title": "Maintenance",
    "assets": {
        "title": "Assets",
        "addAsset": "Add Asset",
        "name": "Asset Name",
        "serialNumber": "Serial Number",
        "location": "Location",
        "status": "Status",
        "operational": "Operational",
        "needsRepair": "Needs Repair",
        "outOfService": "Out of Service",
        "searchPlaceholder": "Search assets...",
    },
    "workOrders": {
        "title": "Work Orders",
        "addWorkOrder": "Create Work Order",
        "title_field": "Title",
        "priority": "Priority",
        "status": "Status",
        "assignee": "Assignee",
        "dueDate": "Due Date",
        "open": "Open",
        "inProgress": "In Progress",
        "completed": "Completed",
        "cancelled": "Cancelled",
    },
    "preventiveMaintenance": {
        "title": "Preventive Maintenance",
        "schedule": "Schedule",
        "frequency": "Frequency",
        "lastCompleted": "Last Completed",
        "nextDue": "Next Due",
    },
    "tabs": {
        "assets": "Assets",
        "workOrders": "Work Orders",
        "pmSchedules": "PM Schedules",
        "tools": "Tools",
        "warranties": "Warranties",
        "loto": "LOTO",
        "fieldReturns": "Field Returns",
        "budgets": "Budgets",
    },
}

# Expand quality section
d["quality"] = {
    "title": "Quality",
    "inspections": {
        "title": "Inspections",
        "addInspection": "New Inspection",
        "workOrder": "Work Order",
        "product": "Product",
        "type": "Type",
        "date": "Inspection Date",
        "status": "Status",
        "passed": "Passed",
        "failed": "Failed",
        "pending": "Pending",
        "quantityInspected": "Qty Inspected",
        "quantityPassed": "Qty Passed",
        "quantityFailed": "Qty Failed",
        "searchPlaceholder": "Search inspections...",
    },
    "ncrs": {
        "title": "Non-Conformance Reports",
        "addNCR": "Create NCR",
        "severity": "Severity",
        "critical": "Critical",
        "major": "Major",
        "minor": "Minor",
        "rootCause": "Root Cause",
        "containmentAction": "Containment Action",
    },
    "capas": {
        "title": "CAPA",
        "addCAPA": "Create CAPA",
        "correctiveAction": "Corrective Action",
        "preventiveAction": "Preventive Action",
        "effectiveness": "Effectiveness",
    },
    "msa": {
        "title": "MSA Studies",
        "gageRR": "Gage R&R",
        "compute": "Compute GRR",
        "repeatability": "Repeatability",
        "reproducibility": "Reproducibility",
    },
    "capability": {
        "title": "Process Capability",
        "compute": "Compute Cp/Cpk",
        "cpk": "Cpk",
        "cp": "Cp",
        "pp": "Pp",
        "ppk": "Ppk",
    },
    "tabs": {
        "inspections": "Inspections",
        "ncrs": "NCRs",
        "capas": "CAPAs",
        "msa": "MSA",
        "capability": "Capability",
        "complaints": "Complaints",
        "surveys": "Surveys",
        "fai": "FAI",
        "selfInspection": "Self Inspection",
        "labTesting": "Lab Testing",
        "aql": "AQL Sampling",
        "traceability": "Traceability",
        "changePoint": "Change Point",
    },
}

# Expand training section
d["training"] = {
    "title": "Training",
    "certifications": {
        "title": "Certifications",
        "name": "Certification Name",
        "status": "Status",
        "enrolled": "Enrolled",
        "inProgress": "In Progress",
        "completed": "Completed",
        "expired": "Expired",
        "expiryDate": "Expiry Date",
    },
    "programs": {
        "title": "Training Programs",
        "addProgram": "Add Program",
        "name": "Program Name",
        "duration": "Duration",
        "participants": "Participants",
    },
    "records": {
        "title": "Training Records",
        "employee": "Employee",
        "course": "Course",
        "completedDate": "Completed Date",
        "score": "Score",
    },
    "tabs": {
        "certifications": "Certifications",
        "programs": "Programs",
        "records": "Records",
    },
}

# Expand production section
d["production"] = {
    "title": "Production",
    "workOrders": {
        "title": "Work Orders",
        "addWorkOrder": "Create Work Order",
        "woNumber": "WO Number",
        "product": "Product",
        "quantity": "Quantity",
        "status": "Status",
        "planned": "Planned",
        "released": "Released",
        "inProgress": "In Progress",
        "completed": "Completed",
        "priority": "Priority",
        "startDate": "Start Date",
        "dueDate": "Due Date",
    },
    "scheduling": {
        "title": "Scheduling",
        "gantt": "Gantt Chart",
        "calendar": "Calendar",
    },
    "tabs": {
        "workOrders": "Work Orders",
        "scheduling": "Scheduling",
    },
}

# Add executive section
d["executive"] = {
    "title": "Executive Dashboard",
    "kpis": "Key Performance Indicators",
    "northStar": "North Star",
    "riskDashboard": "Risk Dashboard",
    "strategicDirectives": {
        "title": "Strategic Directives",
        "addDirective": "Add Directive",
        "status": "Status",
        "progress": "Progress",
        "active": "Active",
        "completed": "Completed",
        "onHold": "On Hold",
    },
    "nl2sql": {
        "title": "Natural Language Query",
        "placeholder": "Ask a question about your data...",
        "execute": "Execute Query",
    },
}

with open("frontend/src/locales/en.json", "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"Updated en.json with {sum(1 for _ in json.dumps(d).split(','))} entries")
print("Added sections: hr, maintenance, executive")
print("Expanded sections: quality, training, production")

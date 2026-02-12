"""Add ALL missing i18n keys to en.json for complete coverage."""
import json

with open("frontend/src/locales/en.json") as f:
    d = json.load(f)

def ensure(obj, path, value):
    """Set nested key if it doesn't exist."""
    keys = path.split(".")
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    if keys[-1] not in obj:
        obj[keys[-1]] = value

# ===== SHARED COMPONENTS =====

# error-state.tsx
ensure(d, "components.errorState.connectionError", "Connection Error")
ensure(d, "components.errorState.connectionErrorDesc", "Unable to reach the server. Please check your connection and try again.")
ensure(d, "components.errorState.serverError", "Server Error")
ensure(d, "components.errorState.serverErrorDesc", "Something went wrong on our end. Please try again later.")
ensure(d, "components.errorState.noData", "No Data")
ensure(d, "components.errorState.noDataDesc", "No records found matching your criteria.")
ensure(d, "components.errorState.accessDenied", "Access Denied")
ensure(d, "components.errorState.accessDeniedDesc", "You don't have permission to access this resource.")
ensure(d, "components.errorState.notFound", "Not Found")
ensure(d, "components.errorState.notFoundDesc", "The requested resource could not be found.")
ensure(d, "components.errorState.error", "Error")
ensure(d, "components.errorState.errorDesc", "An unexpected error occurred.")
ensure(d, "components.errorState.tryAgain", "Try Again")

# page-guard.tsx
ensure(d, "components.pageGuard.accessRestricted", "Access Restricted")
ensure(d, "components.pageGuard.noPermission", "You don't have permission to access this page.")
ensure(d, "components.pageGuard.returnToDashboard", "Return to Dashboard")

# coming-soon.tsx
ensure(d, "components.comingSoon.defaultMessage", "This feature is currently under development and will be available soon.")
ensure(d, "components.comingSoon.goBack", "Go Back")

# table.tsx
ensure(d, "components.table.noData", "No data")
ensure(d, "components.table.rowsPerPage", "Rows per page:")

# command-palette.tsx
ensure(d, "components.commandPalette.noCommandsFound", "No commands found")
ensure(d, "components.commandPalette.tryDifferentSearch", "Try a different search term")
ensure(d, "components.commandPalette.toToggle", "to toggle")

# barcode-scanner.tsx
ensure(d, "components.scanner.scanComplete", "Scan Complete")
ensure(d, "components.scanner.cameraNotActive", "Camera not active")
ensure(d, "components.scanner.switchCamera", "Switch Camera")
ensure(d, "components.scanner.captureFrame", "Capture Frame")
ensure(d, "components.scanner.stopScanner", "Stop Scanner")

# andon-dashboard.tsx
ensure(d, "components.andon.unknownWorkCenter", "Unknown Work Center")
ensure(d, "components.andon.noActiveAlerts", "No active alerts")
ensure(d, "components.andon.refresh", "Refresh")
ensure(d, "components.andon.toggleFullscreen", "Toggle fullscreen")
ensure(d, "components.andon.ackBy", "Ack by {name}")
ensure(d, "components.andon.triggeredBy", "Triggered by {name}")
ensure(d, "components.andon.allSystemsNormal", "All systems operating normally")

# kanban-board.tsx
ensure(d, "components.kanban.unknownCustomer", "Unknown Customer")
ensure(d, "components.kanban.pipelineValue", "Pipeline Value: ")
ensure(d, "components.kanban.kanbanView", "Kanban view")
ensure(d, "components.kanban.listView", "List view")
ensure(d, "components.kanban.calendarView", "Calendar view")

# quick-actions-bar.tsx
ensure(d, "components.quickActions.confirmAction", "Confirm Action")

# CorrectionUI.tsx
ensure(d, "components.correction.submissionFailed", "Correction submission failed")
ensure(d, "components.correction.rejectionFailed", "Rejection submission failed")

# sync-status.tsx
ensure(d, "components.sync.removeOperation", "Remove operation")

# pdf-preview.tsx
ensure(d, "components.pdfPreview.immutableVersion", "Immutable version")
ensure(d, "components.pdfPreview.pdfPreview", "PDF Preview")
ensure(d, "components.pdfPreview.versionHistory", "Version History")
ensure(d, "components.pdfPreview.metadata", "Metadata")
ensure(d, "components.pdfPreview.closeEscape", "Close (Escape)")
ensure(d, "components.pdfPreview.previousPage", "Previous Page")
ensure(d, "components.pdfPreview.nextPage", "Next Page")
ensure(d, "components.pdfPreview.zoomOut", "Zoom Out")
ensure(d, "components.pdfPreview.zoomIn", "Zoom In")
ensure(d, "components.pdfPreview.rotate", "Rotate")
ensure(d, "components.pdfPreview.fullscreen", "Fullscreen")
ensure(d, "components.pdfPreview.download", "Download")
ensure(d, "components.pdfPreview.print", "Print")
ensure(d, "components.pdfPreview.currentlyViewing", "Currently viewing")
ensure(d, "components.pdfPreview.loadingPdf", "Loading PDF...")
ensure(d, "components.pdfPreview.documentInfo", "Document Info")
ensure(d, "components.pdfPreview.createdBy", "Created By")

# security-privacy.tsx
ensure(d, "components.security.noPermission", "You don't have permission to view this data")
ensure(d, "components.security.allActions", "All Actions")

# spatial-ui.tsx
ensure(d, "components.spatialUi.factoryFloorMap", "Factory floor map")
ensure(d, "components.spatialUi.closePanel", "Close panel")
ensure(d, "components.spatialUi.closePathView", "Close path view")
ensure(d, "components.spatialUi.zoomOut", "Zoom out")
ensure(d, "components.spatialUi.zoomIn", "Zoom in")
ensure(d, "components.spatialUi.resetView", "Reset view")
ensure(d, "components.spatialUi.selectCellDetails", "Select a cell to view details")
ensure(d, "components.spatialUi.currentJob", "Current Job:")
ensure(d, "components.spatialUi.changeStatus", "Change Status:")
ensure(d, "components.spatialUi.orderPath", "Order Path:")
ensure(d, "components.spatialUi.processTime", "Process Time")
ensure(d, "components.spatialUi.wasteRatio", "Waste Ratio")
ensure(d, "components.spatialUi.pathSteps", "Path Steps:")
ensure(d, "components.spatialUi.warRoom.kpi", "Key Performance Indicators")
ensure(d, "components.spatialUi.warRoom.salesPipeline", "Sales Pipeline")
ensure(d, "components.spatialUi.warRoom.productionStatus", "Production Status")
ensure(d, "components.spatialUi.warRoom.qualityMetrics", "Quality Metrics")
ensure(d, "components.spatialUi.warRoom.activeAlerts", "Active Alerts")
ensure(d, "components.spatialUi.warRoom.todaysTimeline", "Today's Timeline")

# session-management.tsx
ensure(d, "components.session.notifications", "Notifications")
ensure(d, "components.session.dismissNotification", "Dismiss notification")

# onboarding-help.tsx
ensure(d, "components.onboarding.productTour", "Product tour")
ensure(d, "components.onboarding.closeTour", "Close tour")
ensure(d, "components.onboarding.helpPanel", "Help panel")
ensure(d, "components.onboarding.closeHelpPanel", "Close help panel")
ensure(d, "components.onboarding.dismissSuggestion", "Dismiss suggestion")
ensure(d, "components.onboarding.toggleAssistant", "Toggle Sensei assistant")
ensure(d, "components.onboarding.dismiss", "Dismiss")
ensure(d, "components.onboarding.searchHelp", "Search help")

# error-experience.tsx
ensure(d, "components.error.somethingWentWrong", "Something went wrong")
ensure(d, "components.error.dismissError", "Dismiss error")
ensure(d, "components.error.dismissBtn", "Dismiss")
ensure(d, "components.error.readOnlyMode", "Read-only mode")
ensure(d, "components.error.resolveConflicts", "Resolve Conflicts")
ensure(d, "components.error.yourChanges", "Your changes")
ensure(d, "components.error.serverVersion", "Server version")
ensure(d, "components.emptyState.noResultsFound", "No results found")
ensure(d, "components.emptyState.noItemsYet", "No items yet")
ensure(d, "components.emptyState.noRfqsInQueue", "No RFQs in queue")
ensure(d, "components.emptyState.noQuotesCreated", "No quotes created")
ensure(d, "components.emptyState.noActiveJobs", "No active jobs")

# print-export.tsx
ensure(d, "components.printExport.cancelExport", "Cancel export")
ensure(d, "components.printExport.close", "Close")
ensure(d, "components.printExport.qrCode", "QR Code")
ensure(d, "components.printExport.dataMatrix", "Data Matrix")

# design-system.tsx
ensure(d, "components.designSystem.openAuditPanel", "Open design system audit panel")
ensure(d, "components.designSystem.auditPanelTitle", "Design System Audit Panel")
ensure(d, "components.designSystem.closeAuditPanel", "Close audit panel")
ensure(d, "components.designSystem.horizontalScale", "Horizontal Scale")
ensure(d, "components.designSystem.verticalScale", "Vertical Scale")
ensure(d, "components.designSystem.fontSizes", "Font Sizes")
ensure(d, "components.designSystem.fontWeights", "Font Weights")
ensure(d, "components.designSystem.designSystemAudit", "Design System Audit")

# factory-floor.tsx
ensure(d, "components.factoryFloor.processing", "Processing...")
ensure(d, "components.factoryFloor.commandReceived", "Command received")
ensure(d, "components.factoryFloor.errorOccurred", "Error occurred")
ensure(d, "components.factoryFloor.voiceDisabled", "Voice commands disabled")

# gantt-chart.tsx
ensure(d, "components.ganttChart.noTasks", "No tasks to visualize in Gantt")
ensure(d, "components.ganttChart.taskName", "Task Name")

# data-visualization.tsx
ensure(d, "components.dataVisualization.noData", "No data")

# timeline.tsx
ensure(d, "components.timeline.noActivity", "No activity yet")

# virtual-table.tsx
ensure(d, "components.virtualTable.noData", "No data available")

# layout/sidebar.tsx
ensure(d, "components.sidebar.senseiHome", "Sensei OS home")
ensure(d, "components.sidebar.toggleDarkMode", "Toggle dark mode")
ensure(d, "components.sidebar.administration", "Administration")

# layout/mobile-nav.tsx
ensure(d, "components.mobileNav.navigation", "Mobile navigation")
ensure(d, "components.mobileNav.openMenu", "Open menu")

# ===== PAGE FILES =====

# HR page
ensure(d, "pages.hr.unassignedRole", "Unassigned Role")
ensure(d, "pages.hr.noDepartment", "No Dept")
ensure(d, "pages.hr.remote", "Remote")
ensure(d, "pages.hr.unknownPosition", "Unknown Position")
ensure(d, "pages.hr.candidateDetails", "Candidate Details")
ensure(d, "pages.hr.searchPersonnel", "Search personnel...")
ensure(d, "pages.hr.searchJobs", "Search jobs...")
ensure(d, "pages.hr.toast.employeeCreated", "Employee created successfully")
ensure(d, "pages.hr.toast.employeeCreatedTitle", "Success")
ensure(d, "pages.hr.toast.employeeTerminated", "Employee record terminated")
ensure(d, "pages.hr.toast.jobCreated", "Job opening created")
ensure(d, "pages.hr.toast.jobDeleted", "Job opening deleted")
ensure(d, "pages.hr.toast.deletionFailed", "Failed to perform deletion")
ensure(d, "pages.hr.toast.applicationSubmitted", "Application submitted")
ensure(d, "pages.hr.toast.applicationMoved", "Application moved to {status}")
ensure(d, "pages.hr.toast.updateStatusFailed", "Failed to update application status")
ensure(d, "pages.hr.toast.leaveSubmitted", "Leave request submitted")
ensure(d, "pages.hr.toast.leaveApproved", "Leave request approved")
ensure(d, "pages.hr.toast.leaveApproveFailed", "Failed to approve leave request")
ensure(d, "pages.hr.toast.leaveRejected", "Leave request rejected")
ensure(d, "pages.hr.toast.leaveRejectFailed", "Failed to reject leave request")
ensure(d, "pages.hr.confirmTerminate.title", "Terminate Employee Record")
ensure(d, "pages.hr.confirmTerminate.description", "Are you sure you want to terminate this employee record? This action cannot be undone.")
ensure(d, "pages.hr.confirmDeleteJob.title", "Delete Job Opening")
ensure(d, "pages.hr.confirmDeleteJob.description", "Are you sure you want to delete this job opening?")
ensure(d, "pages.hr.placeholders.email", "john.doe@company.com")
ensure(d, "pages.hr.placeholders.selectRegion", "Select region")
ensure(d, "pages.hr.placeholders.selectStatus", "Select status")
ensure(d, "pages.hr.placeholders.jobDescription", "Job description...")
ensure(d, "pages.hr.placeholders.requiredSkills", "Required skills...")
ensure(d, "pages.hr.placeholders.selectPosition", "Select position")
ensure(d, "pages.hr.placeholders.firstName", "John")
ensure(d, "pages.hr.placeholders.lastName", "Doe")
ensure(d, "pages.hr.placeholders.personalEmail", "john.doe@email.com")
ensure(d, "pages.hr.placeholders.portfolioUrl", "https://...")
ensure(d, "pages.hr.placeholders.additionalNotes", "Additional notes...")
ensure(d, "pages.hr.placeholders.selectEmployee", "Select employee")
ensure(d, "pages.hr.placeholders.leaveReason", "Reason for leave...")

# CTQ pages
ensure(d, "pages.ctq.toast.error", "Error")
ensure(d, "pages.ctq.toast.loadFailed", "Failed to load CTQ details")
ensure(d, "pages.ctq.toast.success", "Success")
ensure(d, "pages.ctq.toast.deleted", "CTQ deleted successfully")
ensure(d, "pages.ctq.toast.deleteFailed", "Failed to delete CTQ")
ensure(d, "pages.ctq.toast.measurementAdded", "Measurement added successfully")
ensure(d, "pages.ctq.toast.measurementFailed", "Failed to add measurement")
ensure(d, "pages.ctq.toast.exportStarted", "Export started")
ensure(d, "pages.ctq.toast.exportStartedDesc", "Your CTQ report is being generated")
ensure(d, "pages.ctq.detail.specificationDetails", "Specification Details")
ensure(d, "pages.ctq.detail.qualityRequirements", "Quality characteristic requirements")
ensure(d, "pages.ctq.detail.nominalValue", "Nominal Value")
ensure(d, "pages.ctq.detail.upperTolerance", "Upper Tolerance")
ensure(d, "pages.ctq.detail.lowerTolerance", "Lower Tolerance")
ensure(d, "pages.ctq.detail.relatedRfq", "Related RFQ")
ensure(d, "pages.ctq.detail.partNumber", "Part Number")
ensure(d, "pages.ctq.detail.measurementInfo", "Measurement Information")
ensure(d, "pages.ctq.detail.howMeasured", "How this characteristic is measured")
ensure(d, "pages.ctq.detail.measurementMethod", "Measurement Method")
ensure(d, "pages.ctq.detail.samplingPlan", "Sampling Plan")
ensure(d, "pages.ctq.detail.checkStage", "Check Stage")
ensure(d, "pages.ctq.detail.evidenceRequired", "Evidence Required")
ensure(d, "pages.ctq.detail.lastUpdated", "Last Updated")
ensure(d, "pages.ctq.detail.measurementHistory", "Measurement History")
ensure(d, "pages.ctq.detail.recentResults", "Recent measurement results and trends")
ensure(d, "pages.ctq.detail.measuredBy", "Measured By")
ensure(d, "pages.ctq.detail.deleteCtq", "Delete CTQ")
ensure(d, "pages.ctq.detail.addMeasurement", "Add Measurement")
ensure(d, "pages.ctq.detail.measuredValue", "Measured Value")
ensure(d, "pages.ctq.detail.notMeasured", "Not Measured")
ensure(d, "pages.ctq.measurementNotesPlaceholder", "Add any relevant notes about this measurement")

# Obeya pages
ensure(d, "pages.obeya.toast.loadFailed", "Failed to load Obeya item data")
ensure(d, "pages.obeya.toast.itemDeleted", "Item deleted successfully")
ensure(d, "pages.obeya.toast.deleteFailed", "Failed to delete item")
ensure(d, "pages.obeya.toast.commentAdded", "Comment added")
ensure(d, "pages.obeya.toast.commentFailed", "Failed to add comment")
ensure(d, "pages.obeya.toast.statusUpdated", "Status Updated")
ensure(d, "pages.obeya.toast.statusFailed", "Failed to update status")
ensure(d, "pages.obeya.toast.created", "Obeya Board Created")
ensure(d, "pages.obeya.toast.createdDesc", "Your new digital obeya board has been successfully initialized.")

# A3 pages
ensure(d, "pages.a3.toast.titleRequired", "Please enter a title for the A3 report.")
ensure(d, "pages.a3.toast.created", "A3 Report Created")
ensure(d, "pages.a3.toast.createdDesc", "The new A3 report has been successfully initialized.")
ensure(d, "pages.a3.toast.createFailed", "Failed to create A3 report.")
ensure(d, "pages.a3.toast.loadFailed", "Failed to load A3 details")
ensure(d, "pages.a3.toast.export", "Export")
ensure(d, "pages.a3.toast.exportDesc", "Starting PDF export...")
ensure(d, "pages.a3.toast.updated", "A3 Report Updated")
ensure(d, "pages.a3.toast.updatedDesc", "Changes have been saved successfully.")
ensure(d, "pages.a3.toast.updateFailed", "Failed to update A3 report.")

# Exceptions page
ensure(d, "pages.exceptions.synchronizing", "Synchronizing operational exceptions")
ensure(d, "pages.exceptions.zeroHighUrgency", "Zero high-urgency nodes identified")

# Warehouse - additional labels
ensure(d, "pages.warehouse.searchDescription", "Search and manage all warehouse inventory")
ensure(d, "pages.warehouse.searchPlaceholder", "Search items…")
ensure(d, "pages.warehouse.itemName", "Item Name")
ensure(d, "pages.warehouse.onHand", "On Hand")
ensure(d, "pages.warehouse.managePO", "Manage purchase order receipts and incoming materials")
ensure(d, "pages.warehouse.poReference", "PO Reference")
ensure(d, "pages.warehouse.expectedDate", "Expected Date")
ensure(d, "pages.warehouse.inTransit", "In Transit")
ensure(d, "pages.warehouse.manageShipments", "Manage shipments and delivery logistics")
ensure(d, "pages.warehouse.shipDate", "Ship Date")
ensure(d, "pages.warehouse.activePickLists", "Active pick lists and order fulfillment")
ensure(d, "pages.warehouse.itemsPicked", "items picked")

# Quotes pages
ensure(d, "pages.quotes.toast.savedDraft", "Quote saved as draft")
ensure(d, "pages.quotes.toast.submitted", "Quote submitted for approval")
ensure(d, "pages.quotes.toast.saveFailed", "Error saving quote")
ensure(d, "pages.quotes.toast.tryAgain", "Please try again.")
ensure(d, "pages.quotes.new.materialCost", "Material Cost")
ensure(d, "pages.quotes.new.laborCost", "Labor Cost")
ensure(d, "pages.quotes.new.overheadCost", "Overhead Cost")
ensure(d, "pages.quotes.new.lineItemNotes", "Line Item Notes")
ensure(d, "pages.quotes.new.noAssumptions", "No assumptions defined")
ensure(d, "pages.quotes.new.newQuote", "New Quote")
ensure(d, "pages.quotes.new.viewVersionHistory", "View Version History")
ensure(d, "pages.quotes.new.lineItems", "Line Items")
ensure(d, "pages.quotes.new.addProductsPricing", "Add products and pricing")
ensure(d, "pages.quotes.new.toggleCostBreakdown", "Toggle detailed cost breakdown")
ensure(d, "pages.quotes.new.noLineItems", "No line items")
ensure(d, "pages.quotes.new.addItemsToQuote", "Add items to your quote")
ensure(d, "pages.quotes.new.unitPrice", "Unit Price")
ensure(d, "pages.quotes.new.totalCost", "Total Cost")
ensure(d, "pages.quotes.new.internalCostingAnalysis", "Internal Costing Analysis")
ensure(d, "pages.quotes.new.totalRevenue", "Total Revenue")
ensure(d, "pages.quotes.new.grossProfit", "Gross Profit")
ensure(d, "pages.quotes.new.termsAndConditions", "Terms and Conditions...")
ensure(d, "pages.quotes.new.internalNotes", "Internal Notes...")
ensure(d, "pages.quotes.new.validUntil", "Valid Until")
ensure(d, "pages.quotes.new.taxRate", "Tax Rate")
ensure(d, "pages.quotes.new.quickActions", "Quick Actions")
ensure(d, "pages.quotes.new.submitForApproval", "Submit Quote for Approval")
ensure(d, "pages.quotes.new.assumptionsVerified", "Assumptions Verified")
ensure(d, "pages.quotes.new.warningsPresent", "Warnings Present")

# Sales / RFQ page-refined
ensure(d, "pages.sales.noBid", "No Bid")
ensure(d, "pages.sales.statusNew", "New")
ensure(d, "pages.sales.statusReviewing", "Reviewing")
ensure(d, "pages.sales.statusQuoting", "Quoting")
ensure(d, "pages.sales.statusSubmitted", "Submitted")
ensure(d, "pages.sales.totalRfqs", "Total RFQs")
ensure(d, "pages.sales.totalValue", "Total Value")
ensure(d, "pages.sales.avgResponseTime", "Avg Response Time")
ensure(d, "pages.sales.conversionRate", "Conversion Rate")
ensure(d, "pages.sales.allStatus", "All Status")
ensure(d, "pages.sales.allPriority", "All Priority")
ensure(d, "pages.sales.dueDate", "Due Date")
ensure(d, "pages.sales.receivedDate", "Received Date")
ensure(d, "pages.sales.searchRfqs", "Search RFQs...")

# Customers page
ensure(d, "pages.customers.toast.deactivated", "Customer deactivated")

# Quoting helper
ensure(d, "pages.quotingHelper.noQuoteFound", "No Quote Found")
ensure(d, "pages.quotingHelper.toast.handoffSuccess", "NPI Handoff Successful")
ensure(d, "pages.quotingHelper.toast.handoffFailed", "Handoff Failed")

# Project management
ensure(d, "pages.projectManagement.toast.settingsSaved", "Settings saved")
ensure(d, "pages.projectManagement.toast.settingsSavedDesc", "Project settings have been updated.")
ensure(d, "pages.projectManagement.toast.saveFailed", "Failed to save")
ensure(d, "pages.projectManagement.toast.saveFailedDesc", "There was an error saving your changes.")
ensure(d, "pages.projectManagement.kanban.columns.new", "New")
ensure(d, "pages.projectManagement.kanban.columns.ready", "Ready")
ensure(d, "pages.projectManagement.kanban.columns.inProgress", "In Progress")
ensure(d, "pages.projectManagement.kanban.columns.readyForTest", "Ready for Test")
ensure(d, "pages.projectManagement.kanban.columns.done", "Done")
ensure(d, "pages.projectManagement.milestones.namePlaceholder", "Phase 1 Complete")
ensure(d, "pages.projectManagement.milestones.detailsPlaceholder", "Details...")
ensure(d, "pages.projectManagement.wiki.searchPlaceholder", "Search...")
ensure(d, "pages.projectManagement.wiki.titlePlaceholder", "Page Title")

# Analytics
ensure(d, "pages.analytics.statusOptimal", "OPTIMAL")

# Andon settings
ensure(d, "pages.andon.toast.settingsSaved", "Signal notification preferences have been updated.")

# Admin
ensure(d, "pages.admin.import.conflictResolution", "Conflict Resolution")
ensure(d, "pages.admin.import.skipExisting", "Skip Existing")
ensure(d, "pages.admin.import.updateExisting", "Update Existing")

# Training
ensure(d, "common.loading", "Loading...")

with open("frontend/src/locales/en.json", "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("Done - added all missing i18n keys to en.json")

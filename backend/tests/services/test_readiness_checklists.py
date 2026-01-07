"""
Tests for Readiness Checklists Service.

Tests cover:
- Template management
- Supplier Readiness checklists
- PPAP-lite checklists
- Item status management
- Progress tracking and blocking logic
- Approval workflow
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.readiness_checklists import (
    Checklist,
    ChecklistStatus,
    ChecklistType,
    ItemPriority,
    ItemStatus,
    PPAPLevel,
    ReadinessChecklistsService,
)


@pytest.fixture
def service() -> ReadinessChecklistsService:
    """Create a fresh service instance."""
    return ReadinessChecklistsService()


@pytest.fixture
def supplier_checklist(service: ReadinessChecklistsService) -> Checklist:
    """Create a sample supplier readiness checklist."""
    return service.create_supplier_readiness_checklist(
        supplier_id=uuid4(),
        npi_project_id=uuid4(),
    )


@pytest.fixture
def ppap_checklist(service: ReadinessChecklistsService) -> Checklist:
    """Create a sample PPAP checklist."""
    return service.create_ppap_checklist(
        supplier_id=uuid4(),
        product_id=uuid4(),
        ppap_level=PPAPLevel.LEVEL_3,
    )


class TestTemplateManagement:
    """Tests for template management."""
    
    def test_get_templates_all(self, service: ReadinessChecklistsService) -> None:
        """Test getting all templates."""
        templates = service.get_templates()
        
        assert len(templates) >= 2  # Supplier Readiness and PPAP-lite
    
    def test_get_templates_by_type(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test filtering templates by type."""
        supplier_templates = service.get_templates(
            checklist_type=ChecklistType.SUPPLIER_READINESS,
        )
        ppap_templates = service.get_templates(
            checklist_type=ChecklistType.PPAP_LITE,
        )
        
        assert len(supplier_templates) >= 1
        assert len(ppap_templates) >= 1
        
        for t in supplier_templates:
            assert t.checklist_type == ChecklistType.SUPPLIER_READINESS
    
    def test_get_template_by_id(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test getting template by ID."""
        templates = service.get_templates()
        template_id = templates[0].id
        
        template = service.get_template(template_id)
        
        assert template is not None
        assert template.id == template_id
    
    def test_get_template_by_type(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test getting default template by type."""
        template = service.get_template_by_type(ChecklistType.SUPPLIER_READINESS)
        
        assert template is not None
        assert template.checklist_type == ChecklistType.SUPPLIER_READINESS
    
    def test_create_custom_template(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test creating a custom template."""
        sections = [
            {
                "id": "custom_section",
                "name": "Custom Section",
                "sequence": 1,
                "items": [
                    {
                        "id": "custom_1",
                        "name": "Custom Item",
                        "priority": "major",
                    },
                ],
            },
        ]
        
        template = service.create_template(
            name="Custom Checklist",
            checklist_type=ChecklistType.CUSTOM,
            sections=sections,
            description="A custom checklist template",
        )
        
        assert template.id is not None
        assert template.name == "Custom Checklist"
        assert template.checklist_type == ChecklistType.CUSTOM


class TestSupplierReadinessChecklist:
    """Tests for supplier readiness checklists."""
    
    def test_create_supplier_readiness_checklist(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test creating a supplier readiness checklist."""
        supplier_id = uuid4()
        
        checklist = service.create_supplier_readiness_checklist(
            supplier_id=supplier_id,
        )
        
        assert checklist.id is not None
        assert checklist.checklist_type == ChecklistType.SUPPLIER_READINESS
        assert checklist.supplier_id == supplier_id
        assert checklist.status == ChecklistStatus.NOT_STARTED
    
    def test_supplier_checklist_has_sections(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that supplier checklist has expected sections."""
        section_ids = [s.id for s in supplier_checklist.sections]
        
        assert "quality_system" in section_ids
        assert "capacity" in section_ids
        assert "logistics" in section_ids
        assert "commercial" in section_ids
    
    def test_supplier_checklist_has_items(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that supplier checklist has items."""
        all_items = supplier_checklist.get_all_items()
        
        assert len(all_items) > 0
        
        # Should have critical items
        critical = [i for i in all_items if i.priority == ItemPriority.CRITICAL]
        assert len(critical) > 0
    
    def test_supplier_checklist_completion_zero(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test completion percentage starts at zero."""
        percentage = supplier_checklist.get_completion_percentage()
        
        assert percentage == Decimal("0")
    
    def test_supplier_checklist_blocking_items(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting blocking items."""
        blocking = supplier_checklist.get_blocking_items()
        
        # All critical/major items should be blocking initially
        assert len(blocking) > 0


class TestPPAPChecklist:
    """Tests for PPAP-lite checklists."""
    
    def test_create_ppap_checklist(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test creating a PPAP checklist."""
        supplier_id = uuid4()
        product_id = uuid4()
        
        checklist = service.create_ppap_checklist(
            supplier_id=supplier_id,
            product_id=product_id,
            ppap_level=PPAPLevel.LEVEL_3,
        )
        
        assert checklist.id is not None
        assert checklist.checklist_type == ChecklistType.PPAP_LITE
        assert checklist.ppap_level == PPAPLevel.LEVEL_3
        assert checklist.supplier_id == supplier_id
        assert checklist.product_id == product_id
    
    def test_ppap_checklist_with_customer_requirements(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test PPAP checklist with customer-specific requirements."""
        requirements = ["Full material traceability", "100% inspection on CTQs"]
        
        checklist = service.create_ppap_checklist(
            supplier_id=uuid4(),
            product_id=uuid4(),
            customer_requirements=requirements,
        )
        
        assert checklist.customer_specific_requirements == requirements
    
    def test_ppap_checklist_has_sections(
        self,
        service: ReadinessChecklistsService,
        ppap_checklist: Checklist,
    ) -> None:
        """Test that PPAP checklist has expected sections."""
        section_ids = [s.id for s in ppap_checklist.sections]
        
        assert "design_records" in section_ids
        assert "process_documentation" in section_ids
        assert "measurement" in section_ids
        assert "samples" in section_ids
        assert "approval" in section_ids
    
    def test_get_ppap_status(
        self,
        service: ReadinessChecklistsService,
        ppap_checklist: Checklist,
    ) -> None:
        """Test getting PPAP-specific status."""
        status = service.get_ppap_status(ppap_checklist.id)
        
        assert status is not None
        assert status["ppap_level"] == PPAPLevel.LEVEL_3.value
        assert status["ready_for_submission"] is False
        assert "elements" in status
    
    def test_ppap_levels(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test different PPAP levels."""
        for level in PPAPLevel:
            checklist = service.create_ppap_checklist(
                supplier_id=uuid4(),
                product_id=uuid4(),
                ppap_level=level,
            )
            
            assert checklist.ppap_level == level


class TestChecklistRetrieval:
    """Tests for checklist retrieval."""
    
    def test_get_checklist(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test retrieving a checklist."""
        retrieved = service.get_checklist(supplier_checklist.id)
        
        assert retrieved is not None
        assert retrieved.id == supplier_checklist.id
    
    def test_get_nonexistent_checklist(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test retrieving non-existent checklist."""
        result = service.get_checklist(uuid4())
        assert result is None
    
    def test_list_checklists(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test listing checklists."""
        service.create_supplier_readiness_checklist(supplier_id=uuid4())
        service.create_ppap_checklist(supplier_id=uuid4(), product_id=uuid4())
        
        checklists = service.list_checklists()
        
        assert len(checklists) == 2
    
    def test_list_checklists_by_type(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test filtering checklists by type."""
        service.create_supplier_readiness_checklist(supplier_id=uuid4())
        service.create_supplier_readiness_checklist(supplier_id=uuid4())
        service.create_ppap_checklist(supplier_id=uuid4(), product_id=uuid4())
        
        supplier_checklists = service.list_checklists(
            checklist_type=ChecklistType.SUPPLIER_READINESS,
        )
        
        assert len(supplier_checklists) == 2
    
    def test_list_checklists_by_supplier(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test filtering checklists by supplier."""
        supplier_id = uuid4()
        
        service.create_supplier_readiness_checklist(supplier_id=supplier_id)
        service.create_ppap_checklist(
            supplier_id=supplier_id,
            product_id=uuid4(),
        )
        service.create_supplier_readiness_checklist(supplier_id=uuid4())
        
        supplier_checklists = service.get_supplier_checklists(supplier_id)
        
        assert len(supplier_checklists) == 2
    
    def test_list_checklists_by_project(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test filtering checklists by NPI project."""
        project_id = uuid4()
        
        service.create_supplier_readiness_checklist(
            supplier_id=uuid4(),
            npi_project_id=project_id,
        )
        service.create_supplier_readiness_checklist(
            supplier_id=uuid4(),
        )
        
        project_checklists = service.get_project_checklists(project_id)
        
        assert len(project_checklists) == 1


class TestItemManagement:
    """Tests for checklist item management."""
    
    def test_get_item(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting a specific item."""
        items = supplier_checklist.get_all_items()
        item_id = items[0].id
        
        item = service.get_item(supplier_checklist.id, item_id)
        
        assert item is not None
        assert item.id == item_id
    
    def test_get_nonexistent_item(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting non-existent item."""
        item = service.get_item(supplier_checklist.id, uuid4())
        assert item is None
    
    def test_update_item_status(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test updating item status."""
        items = supplier_checklist.get_all_items()
        item = items[0]
        user_id = uuid4()
        
        updated = service.update_item_status(
            supplier_checklist.id,
            item.id,
            status=ItemStatus.IN_PROGRESS,
            notes="Working on this",
            completed_by=user_id,
        )
        
        assert updated is not None
        assert updated.status == ItemStatus.IN_PROGRESS
        assert updated.status_notes == "Working on this"
    
    def test_complete_item(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test completing an item."""
        items = supplier_checklist.get_all_items()
        item = items[0]
        user_id = uuid4()
        
        updated = service.update_item_status(
            supplier_checklist.id,
            item.id,
            status=ItemStatus.COMPLETE,
            completed_by=user_id,
        )
        
        assert updated is not None
        assert updated.status == ItemStatus.COMPLETE
        assert updated.completed_by == user_id
        assert updated.completed_at is not None
        assert updated.is_satisfied() is True
    
    def test_add_item_evidence(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test adding evidence to an item."""
        items = supplier_checklist.get_all_items()
        item = items[0]
        attachment_id = uuid4()
        
        updated = service.add_item_evidence(
            supplier_checklist.id,
            item.id,
            attachment_ids=[attachment_id],
            notes="ISO certificate attached",
        )
        
        assert updated is not None
        assert attachment_id in updated.attachment_ids
        assert "ISO certificate" in updated.evidence_notes
        assert updated.evidence_provided is True
        # Should auto-update to in_progress
        assert updated.status == ItemStatus.IN_PROGRESS
    
    def test_approve_item(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test approving an item."""
        # Find an item that requires approval
        items = supplier_checklist.get_all_items()
        item = items[0]
        approver_id = uuid4()
        
        approved = service.approve_item(
            supplier_checklist.id,
            item.id,
            approved_by=approver_id,
        )
        
        assert approved is not None
        assert approved.approved is True
        assert approved.approved_by == approver_id
        assert approved.approved_at is not None
        assert approved.status == ItemStatus.COMPLETE
    
    def test_waive_item(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test waiving an item."""
        items = supplier_checklist.get_all_items()
        item = items[0]
        waiver_id = uuid4()
        expiration = datetime.now(timezone.utc) + timedelta(days=90)
        
        waived = service.waive_item(
            supplier_checklist.id,
            item.id,
            waived_by=waiver_id,
            reason="Customer approved alternative",
            expiration=expiration,
        )
        
        assert waived is not None
        assert waived.status == ItemStatus.WAIVED
        assert waived.waived is True
        assert waived.waived_by == waiver_id
        assert waived.waiver_reason == "Customer approved alternative"
        assert waived.waiver_expiration == expiration
        assert waived.is_satisfied() is True
    
    def test_mark_item_not_applicable(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test marking item as not applicable."""
        items = supplier_checklist.get_all_items()
        item = items[0]
        user_id = uuid4()
        
        na = service.mark_item_not_applicable(
            supplier_checklist.id,
            item.id,
            reason="Not relevant for this product type",
            marked_by=user_id,
        )
        
        assert na is not None
        assert na.status == ItemStatus.NOT_APPLICABLE
        assert na.is_satisfied() is True


class TestChecklistProgress:
    """Tests for checklist progress tracking."""
    
    def test_completion_percentage_increases(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that completion percentage increases as items complete."""
        initial = supplier_checklist.get_completion_percentage()
        assert initial == Decimal("0")
        
        items = supplier_checklist.get_all_items()
        
        # Complete some items
        for item in items[:3]:
            service.update_item_status(
                supplier_checklist.id,
                item.id,
                ItemStatus.COMPLETE,
            )
        
        # Refresh checklist
        updated = service.get_checklist(supplier_checklist.id)
        new_percentage = updated.get_completion_percentage()
        
        assert new_percentage > initial
    
    def test_blocking_items_decrease(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that blocking items decrease as items complete."""
        initial_blocking = len(supplier_checklist.get_blocking_items())
        assert initial_blocking > 0
        
        items = supplier_checklist.get_all_items()
        blocking_items = [i for i in items if i.is_blocking()]
        
        # Complete a blocking item
        if blocking_items:
            service.update_item_status(
                supplier_checklist.id,
                blocking_items[0].id,
                ItemStatus.COMPLETE,
            )
        
        updated = service.get_checklist(supplier_checklist.id)
        new_blocking = len(updated.get_blocking_items())
        
        assert new_blocking < initial_blocking
    
    def test_checklist_status_updates_automatically(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that checklist status updates as items are completed."""
        assert supplier_checklist.status == ChecklistStatus.NOT_STARTED
        
        items = supplier_checklist.get_all_items()
        
        # Start working on an item
        service.update_item_status(
            supplier_checklist.id,
            items[0].id,
            ItemStatus.IN_PROGRESS,
        )
        
        updated = service.get_checklist(supplier_checklist.id)
        assert updated.status == ChecklistStatus.IN_PROGRESS
    
    def test_checklist_complete_when_all_satisfied(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that checklist is complete when all items satisfied."""
        items = supplier_checklist.get_all_items()
        
        # Complete all items
        for item in items:
            service.update_item_status(
                supplier_checklist.id,
                item.id,
                ItemStatus.COMPLETE,
            )
        
        updated = service.get_checklist(supplier_checklist.id)
        
        assert updated.is_complete() is True
        assert updated.get_completion_percentage() == Decimal("100")
    
    def test_get_checklist_summary(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting checklist summary."""
        summary = service.get_checklist_summary(supplier_checklist.id)
        
        assert summary is not None
        assert summary["checklist_id"] == supplier_checklist.id
        assert summary["total_items"] > 0
        assert "completion_percentage" in summary
        assert "status_counts" in summary
        assert "sections" in summary
    
    def test_get_blocking_items_report(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting blocking items report."""
        blocking = service.get_blocking_items(supplier_checklist.id)
        
        assert len(blocking) > 0
        
        for item in blocking:
            assert "id" in item
            assert "name" in item
            assert "priority" in item
            assert item["priority"] in ("critical", "major")


class TestChecklistApproval:
    """Tests for checklist approval workflow."""
    
    def test_submit_for_review(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test submitting checklist for review."""
        # Complete all items first
        items = supplier_checklist.get_all_items()
        for item in items:
            service.update_item_status(
                supplier_checklist.id,
                item.id,
                ItemStatus.COMPLETE,
            )
        
        submitted = service.submit_for_review(supplier_checklist.id)
        
        assert submitted is not None
        assert submitted.status == ChecklistStatus.PENDING_REVIEW
    
    def test_cannot_submit_incomplete_checklist(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test that incomplete checklist cannot be submitted."""
        # Don't complete items
        
        result = service.submit_for_review(supplier_checklist.id)
        
        assert result is None
    
    def test_approve_checklist(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test approving a checklist."""
        approver_id = uuid4()
        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        
        approved = service.approve_checklist(
            supplier_checklist.id,
            approved_by=approver_id,
            notes="All requirements verified",
            valid_until=valid_until,
        )
        
        assert approved is not None
        assert approved.status == ChecklistStatus.APPROVED
        assert approved.reviewed_by == approver_id
        assert approved.reviewed_at is not None
        assert approved.review_notes == "All requirements verified"
        assert approved.valid_from is not None
        assert approved.valid_until == valid_until
        assert approved.is_approved() is True
    
    def test_reject_checklist(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test rejecting a checklist."""
        rejector_id = uuid4()
        
        rejected = service.reject_checklist(
            supplier_checklist.id,
            rejected_by=rejector_id,
            reason="Missing critical documentation",
        )
        
        assert rejected is not None
        assert rejected.status == ChecklistStatus.REJECTED
        assert rejected.reviewed_by == rejector_id
        assert rejected.review_notes == "Missing critical documentation"


class TestSectionProgress:
    """Tests for section-level progress tracking."""
    
    def test_section_completion_percentage(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test section completion percentage."""
        section = supplier_checklist.sections[0]
        
        initial = section.get_completion_percentage()
        assert initial == Decimal("0")
        
        # Complete half the items
        for item in section.items[: len(section.items) // 2]:
            service.update_item_status(
                supplier_checklist.id,
                item.id,
                ItemStatus.COMPLETE,
            )
        
        # Refresh section
        updated = service.get_checklist(supplier_checklist.id)
        updated_section = updated.sections[0]
        
        new_percentage = updated_section.get_completion_percentage()
        assert new_percentage > Decimal("0")
    
    def test_section_blocking_items(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting section blocking items."""
        section = supplier_checklist.sections[0]
        
        blocking = section.get_blocking_items()
        
        # Should have blocking items initially
        for item in blocking:
            assert item.priority in (ItemPriority.CRITICAL, ItemPriority.MAJOR)
            assert not item.is_satisfied()


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_create_checklist_without_template(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test creating checklist when no template exists."""
        checklist = service.create_checklist(
            checklist_type=ChecklistType.CUSTOM,
            name="Custom Checklist",
        )
        
        assert checklist is not None
        assert len(checklist.sections) == 0
    
    def test_update_nonexistent_item(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test updating non-existent item."""
        result = service.update_item_status(
            supplier_checklist.id,
            uuid4(),
            ItemStatus.COMPLETE,
        )
        
        assert result is None
    
    def test_ppap_status_for_non_ppap_checklist(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test getting PPAP status for non-PPAP checklist."""
        result = service.get_ppap_status(supplier_checklist.id)
        
        assert result is None
    
    def test_item_is_blocking_logic(
        self,
        service: ReadinessChecklistsService,
        supplier_checklist: Checklist,
    ) -> None:
        """Test item blocking logic."""
        items = supplier_checklist.get_all_items()
        
        # Find critical and minor items
        critical = next(
            (i for i in items if i.priority == ItemPriority.CRITICAL),
            None,
        )
        minor = next(
            (i for i in items if i.priority == ItemPriority.MINOR),
            None,
        )
        
        if critical:
            assert critical.is_blocking() is True
        
        if minor:
            assert minor.is_blocking() is False  # Minor items don't block
    
    def test_list_checklists_by_status(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test filtering checklists by status."""
        c1 = service.create_supplier_readiness_checklist(supplier_id=uuid4())
        c2 = service.create_supplier_readiness_checklist(supplier_id=uuid4())
        
        service.approve_checklist(c2.id, approved_by=uuid4())
        
        approved = service.list_checklists(status=ChecklistStatus.APPROVED)
        not_started = service.list_checklists(status=ChecklistStatus.NOT_STARTED)
        
        assert len(approved) == 1
        assert len(not_started) == 1


class TestCompleteWorkflow:
    """Integration tests for complete workflows."""
    
    def test_complete_supplier_readiness_workflow(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test complete supplier readiness workflow."""
        # Create checklist
        checklist = service.create_supplier_readiness_checklist(
            supplier_id=uuid4(),
            npi_project_id=uuid4(),
        )
        
        assert checklist.status == ChecklistStatus.NOT_STARTED
        
        # Work through items
        items = checklist.get_all_items()
        for item in items:
            # Add evidence
            service.add_item_evidence(
                checklist.id,
                item.id,
                attachment_ids=[uuid4()],
                notes="Evidence provided",
            )
            
            # Complete item
            service.update_item_status(
                checklist.id,
                item.id,
                ItemStatus.COMPLETE,
            )
        
        # Submit for review
        submitted = service.submit_for_review(checklist.id)
        assert submitted.status == ChecklistStatus.PENDING_REVIEW
        
        # Approve
        approved = service.approve_checklist(
            checklist.id,
            approved_by=uuid4(),
            notes="Supplier approved",
        )
        
        assert approved.status == ChecklistStatus.APPROVED
        assert approved.is_approved() is True
    
    def test_complete_ppap_workflow(
        self,
        service: ReadinessChecklistsService,
    ) -> None:
        """Test complete PPAP workflow."""
        # Create PPAP checklist
        checklist = service.create_ppap_checklist(
            supplier_id=uuid4(),
            product_id=uuid4(),
            ppap_level=PPAPLevel.LEVEL_3,
            customer_requirements=["Additional traceability"],
        )
        
        # Check PPAP status
        ppap_status = service.get_ppap_status(checklist.id)
        assert ppap_status["ready_for_submission"] is False
        
        # Complete all items
        items = checklist.get_all_items()
        for item in items:
            if item.requires_approval:
                service.approve_item(
                    checklist.id,
                    item.id,
                    approved_by=uuid4(),
                )
            else:
                service.update_item_status(
                    checklist.id,
                    item.id,
                    ItemStatus.COMPLETE,
                )
        
        # Check ready for submission
        final = service.get_checklist(checklist.id)
        assert final.is_complete() is True
        
        ppap_status = service.get_ppap_status(checklist.id)
        assert ppap_status["ready_for_submission"] is True

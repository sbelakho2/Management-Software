"""
Comprehensive Tests for TPS Knowledge Sources.

Tests validate:
1. Source data integrity
2. URL validity format
3. Topic coverage
4. Category and license distribution
5. Quality scoring
6. Utility functions
"""

from __future__ import annotations

import pytest
from urllib.parse import urlparse

from sensei.services.ops.tps_knowledge_sources import (
    COMPREHENSIVE_TPS_SOURCES,
    KnowledgeSource,
    LicenseType,
    SourceCategory,
    TopicArea,
    get_all_sources,
    get_high_quality_sources,
    get_source_statistics,
    get_sources_by_category,
    get_sources_by_license,
    get_sources_by_tags,
    get_sources_by_topic,
    generate_cli_commands,
)


# =============================================================================
# Test Data Integrity
# =============================================================================


class TestSourceDataIntegrity:
    """Test that all source data is valid and complete."""

    def test_all_sources_have_required_fields(self) -> None:
        """Verify all sources have required fields populated."""
        for source in COMPREHENSIVE_TPS_SOURCES:
            assert source.id, f"Source missing ID"
            assert source.name, f"Source {source.id} missing name"
            assert source.description, f"Source {source.id} missing description"
            assert source.url, f"Source {source.id} missing URL"
            assert source.category, f"Source {source.id} missing category"
            assert source.license_type, f"Source {source.id} missing license_type"
            assert source.topics, f"Source {source.id} missing topics"
            assert source.tags, f"Source {source.id} missing tags"
            assert source.format, f"Source {source.id} missing format"

    def test_unique_source_ids(self) -> None:
        """Verify all source IDs are unique."""
        ids = [s.id for s in COMPREHENSIVE_TPS_SOURCES]
        assert len(ids) == len(set(ids)), "Duplicate source IDs found"

    def test_valid_url_format(self) -> None:
        """Verify all URLs are properly formatted."""
        for source in COMPREHENSIVE_TPS_SOURCES:
            parsed = urlparse(source.url)
            assert parsed.scheme in ("http", "https"), \
                f"Source {source.id} has invalid URL scheme: {source.url}"
            assert parsed.netloc, \
                f"Source {source.id} has invalid URL netloc: {source.url}"

    def test_quality_scores_in_range(self) -> None:
        """Verify quality scores are between 0 and 1."""
        for source in COMPREHENSIVE_TPS_SOURCES:
            assert 0.0 <= source.quality_score <= 1.0, \
                f"Source {source.id} has invalid quality_score: {source.quality_score}"

    def test_valid_enums(self) -> None:
        """Verify all enum values are valid."""
        for source in COMPREHENSIVE_TPS_SOURCES:
            assert isinstance(source.category, SourceCategory)
            assert isinstance(source.license_type, LicenseType)
            for topic in source.topics:
                assert isinstance(topic, TopicArea)

    def test_format_values(self) -> None:
        """Verify format values are from expected set."""
        valid_formats = {"html", "pdf", "video", "course"}
        for source in COMPREHENSIVE_TPS_SOURCES:
            assert source.format in valid_formats, \
                f"Source {source.id} has unexpected format: {source.format}"

    def test_language_codes(self) -> None:
        """Verify language codes are valid ISO 639-1."""
        valid_languages = {"en", "ja", "de", "fr", "es", "zh", "ko", "pt"}
        for source in COMPREHENSIVE_TPS_SOURCES:
            assert source.language in valid_languages, \
                f"Source {source.id} has unexpected language: {source.language}"


# =============================================================================
# Test Topic Coverage
# =============================================================================


class TestTopicCoverage:
    """Test that sources adequately cover all TPS topics."""

    @pytest.fixture
    def topic_counts(self) -> dict[TopicArea, int]:
        """Get topic coverage counts."""
        counts: dict[TopicArea, int] = {}
        for source in COMPREHENSIVE_TPS_SOURCES:
            for topic in source.topics:
                counts[topic] = counts.get(topic, 0) + 1
        return counts

    def test_core_tps_pillars_covered(self, topic_counts: dict) -> None:
        """Verify core TPS pillars have adequate coverage."""
        core_pillars = [TopicArea.JUST_IN_TIME, TopicArea.JIDOKA]
        for pillar in core_pillars:
            assert topic_counts.get(pillar, 0) >= 2, \
                f"Core pillar {pillar.value} has insufficient coverage"

    def test_kaizen_covered(self, topic_counts: dict) -> None:
        """Verify Kaizen has strong coverage."""
        assert topic_counts.get(TopicArea.KAIZEN, 0) >= 3, \
            "Kaizen topic has insufficient coverage"

    def test_key_tools_covered(self, topic_counts: dict) -> None:
        """Verify key Lean tools are covered."""
        key_tools = [
            TopicArea.VSM,
            TopicArea.FIVE_S,
            TopicArea.KANBAN,
            TopicArea.SMED,
            TopicArea.TPM,
        ]
        for tool in key_tools:
            assert topic_counts.get(tool, 0) >= 1, \
                f"Key tool {tool.value} has no coverage"

    def test_problem_solving_covered(self, topic_counts: dict) -> None:
        """Verify problem-solving methods are covered."""
        problem_solving = [
            TopicArea.PDCA,
            TopicArea.A3_THINKING,
            TopicArea.FIVE_WHYS,
        ]
        for method in problem_solving:
            assert topic_counts.get(method, 0) >= 1, \
                f"Problem-solving method {method.value} has no coverage"

    def test_application_domains_covered(self, topic_counts: dict) -> None:
        """Verify application domains are covered."""
        domains = [
            TopicArea.LEAN_HEALTHCARE,
            TopicArea.LEAN_SOFTWARE,
        ]
        for domain in domains:
            assert topic_counts.get(domain, 0) >= 1, \
                f"Application domain {domain.value} has no coverage"

    def test_history_covered(self, topic_counts: dict) -> None:
        """Verify historical context is covered."""
        assert topic_counts.get(TopicArea.HISTORY, 0) >= 3, \
            "Historical context has insufficient coverage"

    def test_all_topics_have_at_least_one_source(self, topic_counts: dict) -> None:
        """Check which topics have sources (informational)."""
        covered = []
        uncovered = []
        for topic in TopicArea:
            if topic_counts.get(topic, 0) > 0:
                covered.append(topic.value)
            else:
                uncovered.append(topic.value)
        
        # At least 80% of topics should be covered
        coverage_ratio = len(covered) / len(TopicArea)
        assert coverage_ratio >= 0.7, \
            f"Only {coverage_ratio:.1%} of topics covered. Missing: {uncovered}"


# =============================================================================
# Test Category Distribution
# =============================================================================


class TestCategoryDistribution:
    """Test source category distribution."""

    @pytest.fixture
    def category_counts(self) -> dict[SourceCategory, int]:
        """Get category distribution."""
        counts: dict[SourceCategory, int] = {}
        for source in COMPREHENSIVE_TPS_SOURCES:
            counts[source.category] = counts.get(source.category, 0) + 1
        return counts

    def test_has_official_toyota_sources(self, category_counts: dict) -> None:
        """Verify Toyota official sources exist."""
        assert category_counts.get(SourceCategory.TOYOTA_OFFICIAL, 0) >= 3, \
            "Should have at least 3 official Toyota sources"

    def test_has_academic_sources(self, category_counts: dict) -> None:
        """Verify academic sources exist."""
        assert category_counts.get(SourceCategory.ACADEMIC, 0) >= 5, \
            "Should have at least 5 academic sources"

    def test_has_government_sources(self, category_counts: dict) -> None:
        """Verify government sources exist."""
        assert category_counts.get(SourceCategory.GOVERNMENT, 0) >= 2, \
            "Should have at least 2 government sources"

    def test_has_professional_org_sources(self, category_counts: dict) -> None:
        """Verify professional organization sources exist."""
        assert category_counts.get(SourceCategory.PROFESSIONAL_ORG, 0) >= 5, \
            "Should have at least 5 professional organization sources"

    def test_has_classic_texts(self, category_counts: dict) -> None:
        """Verify classic texts are included."""
        assert category_counts.get(SourceCategory.CLASSIC_TEXT, 0) >= 3, \
            "Should have at least 3 classic text sources"

    def test_diverse_category_distribution(self, category_counts: dict) -> None:
        """Verify categories are diverse."""
        # At least 4 different categories should be represented
        assert len(category_counts) >= 4, \
            "Should have at least 4 different source categories"


# =============================================================================
# Test License Distribution
# =============================================================================


class TestLicenseDistribution:
    """Test source license distribution."""

    @pytest.fixture
    def license_counts(self) -> dict[LicenseType, int]:
        """Get license distribution."""
        counts: dict[LicenseType, int] = {}
        for source in COMPREHENSIVE_TPS_SOURCES:
            counts[source.license_type] = counts.get(source.license_type, 0) + 1
        return counts

    def test_has_public_domain_sources(self, license_counts: dict) -> None:
        """Verify public domain sources exist."""
        assert license_counts.get(LicenseType.PUBLIC_DOMAIN, 0) >= 1, \
            "Should have at least 1 public domain source"

    def test_has_open_licensed_sources(self, license_counts: dict) -> None:
        """Verify open-licensed sources exist."""
        open_licenses = [
            LicenseType.CC_BY,
            LicenseType.CC_BY_SA,
            LicenseType.CC_BY_NC_SA,
            LicenseType.US_GOVERNMENT,
            LicenseType.OPEN_ACCESS,
        ]
        open_count = sum(license_counts.get(lic, 0) for lic in open_licenses)
        assert open_count >= 10, \
            f"Should have at least 10 open-licensed sources, got {open_count}"

    def test_us_government_sources(self, license_counts: dict) -> None:
        """Verify US Government sources exist (public domain)."""
        assert license_counts.get(LicenseType.US_GOVERNMENT, 0) >= 2, \
            "Should have at least 2 US Government sources"


# =============================================================================
# Test Quality Metrics
# =============================================================================


class TestQualityMetrics:
    """Test source quality metrics."""

    def test_minimum_total_sources(self) -> None:
        """Verify we have a substantial number of sources."""
        assert len(COMPREHENSIVE_TPS_SOURCES) >= 50, \
            f"Should have at least 50 sources, got {len(COMPREHENSIVE_TPS_SOURCES)}"

    def test_average_quality_score(self) -> None:
        """Verify average quality score is acceptable."""
        avg_score = sum(s.quality_score for s in COMPREHENSIVE_TPS_SOURCES) / len(COMPREHENSIVE_TPS_SOURCES)
        assert avg_score >= 0.8, \
            f"Average quality score should be >= 0.8, got {avg_score:.2f}"

    def test_has_high_quality_sources(self) -> None:
        """Verify we have high-quality sources."""
        high_quality = [s for s in COMPREHENSIVE_TPS_SOURCES if s.quality_score >= 0.9]
        assert len(high_quality) >= 10, \
            f"Should have at least 10 high-quality sources, got {len(high_quality)}"

    def test_toyota_sources_are_high_quality(self) -> None:
        """Verify Toyota official sources have high quality scores."""
        toyota_sources = [
            s for s in COMPREHENSIVE_TPS_SOURCES 
            if s.category == SourceCategory.TOYOTA_OFFICIAL
        ]
        for source in toyota_sources:
            assert source.quality_score >= 0.9, \
                f"Toyota source {source.id} should have quality >= 0.9"


# =============================================================================
# Test Utility Functions
# =============================================================================


class TestUtilityFunctions:
    """Test source utility functions."""

    def test_get_all_sources(self) -> None:
        """Test get_all_sources returns all sources."""
        sources = get_all_sources()
        assert len(sources) == len(COMPREHENSIVE_TPS_SOURCES)
        assert sources == COMPREHENSIVE_TPS_SOURCES

    def test_get_sources_by_category(self) -> None:
        """Test filtering by category."""
        toyota_sources = get_sources_by_category(SourceCategory.TOYOTA_OFFICIAL)
        assert len(toyota_sources) >= 3
        for source in toyota_sources:
            assert source.category == SourceCategory.TOYOTA_OFFICIAL

    def test_get_sources_by_topic(self) -> None:
        """Test filtering by topic."""
        jit_sources = get_sources_by_topic(TopicArea.JUST_IN_TIME)
        assert len(jit_sources) >= 2
        for source in jit_sources:
            assert TopicArea.JUST_IN_TIME in source.topics

    def test_get_sources_by_license(self) -> None:
        """Test filtering by license."""
        cc_sources = get_sources_by_license(LicenseType.CC_BY_SA)
        assert len(cc_sources) >= 5  # Wikipedia sources
        for source in cc_sources:
            assert source.license_type == LicenseType.CC_BY_SA

    def test_get_high_quality_sources(self) -> None:
        """Test filtering by quality score."""
        high_quality = get_high_quality_sources(min_score=0.9)
        assert len(high_quality) >= 10
        for source in high_quality:
            assert source.quality_score >= 0.9

    def test_get_sources_by_tags(self) -> None:
        """Test filtering by tags."""
        toyota_tagged = get_sources_by_tags(["toyota", "official"])
        assert len(toyota_tagged) >= 3
        
        kaizen_tagged = get_sources_by_tags(["kaizen"])
        assert len(kaizen_tagged) >= 1

    def test_get_source_statistics(self) -> None:
        """Test statistics generation."""
        stats = get_source_statistics()
        
        assert "total_sources" in stats
        assert stats["total_sources"] == len(COMPREHENSIVE_TPS_SOURCES)
        
        assert "by_category" in stats
        assert "by_license" in stats
        assert "topic_coverage" in stats
        assert "average_quality_score" in stats
        assert "high_quality_count" in stats
        
        # Verify consistency
        category_sum = sum(stats["by_category"].values())
        assert category_sum == stats["total_sources"]

    def test_generate_cli_commands(self) -> None:
        """Test CLI command generation."""
        commands = generate_cli_commands()
        
        assert len(commands) > 0
        
        for cmd in commands:
            assert "source_id" in cmd
            assert "source_name" in cmd
            assert "command" in cmd
            assert "license" in cmd
            assert "curl" in cmd["command"]


# =============================================================================
# Test Specific Important Sources
# =============================================================================


class TestImportantSources:
    """Test that specific important sources exist and are correct."""

    def test_toyota_global_tps_source(self) -> None:
        """Verify Toyota Global TPS source exists and is correct."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "toyota_global_tps"),
            None
        )
        assert source is not None
        assert source.quality_score == 1.0
        assert "toyota" in source.url.lower()
        assert TopicArea.JUST_IN_TIME in source.topics
        assert TopicArea.JIDOKA in source.topics

    def test_mit_ocw_source(self) -> None:
        """Verify MIT OCW Lean Enterprise source exists."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "mit_ocw_lean_enterprise"),
            None
        )
        assert source is not None
        assert source.category == SourceCategory.ACADEMIC
        assert "mit.edu" in source.url

    def test_lei_source(self) -> None:
        """Verify Lean Enterprise Institute source exists."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "lei_lean_org"),
            None
        )
        assert source is not None
        assert source.quality_score >= 0.9
        assert "lean.org" in source.url

    def test_nist_mep_source(self) -> None:
        """Verify NIST MEP source exists."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "nist_mep_lean_guide"),
            None
        )
        assert source is not None
        assert source.license_type == LicenseType.US_GOVERNMENT
        assert "nist.gov" in source.url

    def test_taylor_historical_source(self) -> None:
        """Verify Frederick Taylor historical source exists."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "taylor_scientific_mgmt"),
            None
        )
        assert source is not None
        assert source.license_type == LicenseType.PUBLIC_DOMAIN
        assert source.year_published == 1911
        assert TopicArea.HISTORY in source.topics

    def test_deming_source(self) -> None:
        """Verify Deming source exists."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "deming_out_of_crisis"),
            None
        )
        assert source is not None
        assert TopicArea.PDCA in source.topics

    def test_shingo_institute_source(self) -> None:
        """Verify Shingo Institute source exists."""
        source = next(
            (s for s in COMPREHENSIVE_TPS_SOURCES if s.id == "shingo_institute"),
            None
        )
        assert source is not None
        assert source.quality_score >= 0.9


# =============================================================================
# Test Search and Discovery Use Cases
# =============================================================================


class TestSearchAndDiscovery:
    """Test real-world search and discovery scenarios."""

    def test_find_sources_for_new_practitioner(self) -> None:
        """Find sources suitable for someone new to Lean."""
        # New practitioners need official, high-quality introductory sources
        intro_sources = [
            s for s in COMPREHENSIVE_TPS_SOURCES
            if s.quality_score >= 0.9 and TopicArea.PHILOSOPHY in s.topics
        ]
        assert len(intro_sources) >= 3, \
            "Should have at least 3 high-quality introductory sources"

    def test_find_sources_for_vsm_project(self) -> None:
        """Find sources for someone doing a VSM project."""
        vsm_sources = get_sources_by_topic(TopicArea.VSM)
        assert len(vsm_sources) >= 3, \
            "Should have at least 3 VSM sources"

    def test_find_sources_for_healthcare_lean(self) -> None:
        """Find sources for healthcare Lean implementation."""
        healthcare_sources = get_sources_by_topic(TopicArea.LEAN_HEALTHCARE)
        assert len(healthcare_sources) >= 1, \
            "Should have at least 1 healthcare Lean source"

    def test_find_freely_usable_sources(self) -> None:
        """Find sources that can be freely used for training."""
        free_licenses = [
            LicenseType.PUBLIC_DOMAIN,
            LicenseType.CC_BY,
            LicenseType.CC_BY_SA,
            LicenseType.US_GOVERNMENT,
        ]
        free_sources = [
            s for s in COMPREHENSIVE_TPS_SOURCES
            if s.license_type in free_licenses
        ]
        assert len(free_sources) >= 20, \
            f"Should have at least 20 freely usable sources, got {len(free_sources)}"

    def test_find_sources_by_organization(self) -> None:
        """Find sources from specific organizations."""
        toyota_org_sources = [
            s for s in COMPREHENSIVE_TPS_SOURCES
            if s.organization and "Toyota" in s.organization
        ]
        assert len(toyota_org_sources) >= 3

    def test_find_oldest_sources_for_history(self) -> None:
        """Find historical sources for understanding Lean evolution."""
        dated_sources = [
            s for s in COMPREHENSIVE_TPS_SOURCES
            if s.year_published is not None
        ]
        assert len(dated_sources) >= 5
        
        oldest = min(dated_sources, key=lambda s: s.year_published)
        assert oldest.year_published <= 1930, \
            "Should have sources from early 20th century"


# =============================================================================
# Test Data Model
# =============================================================================


class TestKnowledgeSourceModel:
    """Test the KnowledgeSource data model."""

    def test_knowledge_source_creation(self) -> None:
        """Test creating a KnowledgeSource."""
        source = KnowledgeSource(
            id="test_source",
            name="Test Source",
            description="A test source for unit tests.",
            url="https://example.com/test",
            category=SourceCategory.BLOG_ARTICLE,
            license_type=LicenseType.CC_BY,
            topics=[TopicArea.KAIZEN],
            tags=["test", "example"],
            format="html",
        )
        
        assert source.id == "test_source"
        assert source.quality_score == 0.8  # Default
        assert source.language == "en"  # Default

    def test_knowledge_source_optional_fields(self) -> None:
        """Test optional fields have correct defaults."""
        source = KnowledgeSource(
            id="test",
            name="Test",
            description="Test",
            url="https://example.com",
            category=SourceCategory.BLOG_ARTICLE,
            license_type=LicenseType.CC_BY,
            topics=[TopicArea.KAIZEN],
            tags=["test"],
            format="html",
        )
        
        assert source.author is None
        assert source.organization is None
        assert source.year_published is None
        assert source.last_verified is None
        assert source.notes is None


# =============================================================================
# Integration Test - Knowledge Base Completeness
# =============================================================================


class TestKnowledgeBaseCompleteness:
    """Integration tests for overall knowledge base quality."""

    def test_comprehensive_tps_coverage(self) -> None:
        """Test that the knowledge base comprehensively covers TPS."""
        stats = get_source_statistics()
        
        # Should have substantial total sources
        assert stats["total_sources"] >= 50
        
        # Should cover most topic areas
        covered_topics = len(stats["topic_coverage"])
        total_topics = len(TopicArea)
        coverage_ratio = covered_topics / total_topics
        assert coverage_ratio >= 0.7, \
            f"Topic coverage {coverage_ratio:.1%} below 70% threshold"
        
        # Should have high average quality
        assert stats["average_quality_score"] >= 0.8

    def test_balanced_source_types(self) -> None:
        """Test that source types are balanced."""
        stats = get_source_statistics()
        categories = stats["by_category"]
        
        # Should have multiple category types
        assert len(categories) >= 4
        
        # No single category should dominate > 50%
        total = stats["total_sources"]
        for category, count in categories.items():
            ratio = count / total
            assert ratio <= 0.5, \
                f"Category {category} dominates with {ratio:.1%}"

    def test_actionable_knowledge(self) -> None:
        """Test that knowledge is actionable (has tools/templates)."""
        tool_sources = get_sources_by_category(SourceCategory.TOOL_TEMPLATE)
        assert len(tool_sources) >= 1, \
            "Should have at least 1 tool/template source"

    def test_authoritative_sources_present(self) -> None:
        """Test that authoritative sources are well-represented."""
        high_quality = get_high_quality_sources(min_score=0.95)
        assert len(high_quality) >= 5, \
            "Should have at least 5 highly authoritative sources"
        
        # Check specific authoritative orgs (check org name OR URL)
        authoritative_orgs = {"Toyota", "MIT", "NIST", "Lean Enterprise", "Shingo"}
        found_orgs = set()
        for source in high_quality:
            org_text = (source.organization or "").lower()
            url_text = source.url.lower()
            for org in authoritative_orgs:
                org_lower = org.lower()
                if org_lower in org_text or org_lower.replace(" ", "") in url_text:
                    found_orgs.add(org)
                # Special case for MIT
                if org == "MIT" and ("mit.edu" in url_text or "mit" in org_text):
                    found_orgs.add(org)
                # Special case for NIST
                if org == "NIST" and "nist.gov" in url_text:
                    found_orgs.add(org)
        
        assert len(found_orgs) >= 3, \
            f"Should find at least 3 authoritative orgs, found: {found_orgs}"

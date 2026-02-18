"""Unit tests for the PDF requirements extractor."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import ApplicationConfig, DeepSeekConfig
from src.deepseek_client import DeepSeekClient, DeepSeekAPIError
from src.models import (
    Requirement,
    RequirementPriority,
    RequirementType,
    Section,
    TableOfContentsEntry,
)


class TestDeepSeekConfig:
    """Tests for DeepSeek configuration."""
    
    def test_config_with_api_key(self):
        """Test configuration with valid API key."""
        config = DeepSeekConfig(api_key="test-key-123")
        assert config.api_key == "test-key-123"
        assert config.model == "deepseek-chat"
        assert config.temperature == 0.7
    
    def test_config_without_api_key(self):
        """Test configuration raises error without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY not found"):
                DeepSeekConfig()


class TestModels:
    """Tests for data models."""
    
    def test_requirement_creation(self):
        """Test creating a requirement."""
        req = Requirement(
            id="REQ-001",
            text="System must support 100 concurrent users",
            type=RequirementType.TECHNICAL,
            priority=RequirementPriority.MANDATORY,
        )
        assert req.id == "REQ-001"
        assert req.type == RequirementType.TECHNICAL
        assert req.priority == RequirementPriority.MANDATORY
    
    def test_requirement_to_dict(self):
        """Test converting requirement to dictionary."""
        req = Requirement(
            id="REQ-001",
            text="Test requirement",
            type=RequirementType.FUNCTIONAL,
            reference="GOST 12345",
        )
        data = req.to_dict()
        assert data["id"] == "REQ-001"
        assert data["text"] == "Test requirement"
        assert data["type"] == "Функциональное"
        assert data["reference"] == "GOST 12345"
    
    def test_toc_entry_creation(self):
        """Test creating TOC entry."""
        entry = TableOfContentsEntry(
            level=1,
            number="1",
            title="Introduction",
            page_start=1,
        )
        assert entry.level == 1
        assert entry.number == "1"
        assert entry.title == "Introduction"
        assert entry.page_start == 1
    
    def test_section_page_range(self):
        """Test section page range property."""
        section = Section(
            number="1",
            title="Test Section",
            page_start=1,
            page_end=5,
            raw_text="Test content",
        )
        assert section.page_range == "1-5"
        
        section_no_end = Section(
            number="2",
            title="Last Section",
            page_start=6,
            page_end=None,
            raw_text="Test content",
        )
        assert section_no_end.page_range == "6-end"


class TestDeepSeekClient:
    """Tests for DeepSeek API client."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return DeepSeekConfig(api_key="test-key-123")
    
    @pytest.fixture
    def mock_response(self):
        """Create mock API response."""
        mock = Mock()
        mock.status_code = 200
        mock.json.return_value = {
            "choices": [
                {"message": {"content": '{"test": "data"}'}}
            ]
        }
        return mock
    
    def test_client_initialization(self, config):
        """Test client initialization."""
        with DeepSeekClient(config) as client:
            assert client.config == config
            assert "Bearer test-key-123" in client.headers["Authorization"]
    
    def test_parse_toc_success(self, config, mock_response):
        """Test successful TOC parsing."""
        toc_json = {
            "toc": [
                {
                    "level": 1,
                    "number": "1",
                    "title": "Introduction",
                    "page_start": 1,
                    "children": [],
                }
            ]
        }
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": json.dumps(toc_json)}}
            ]
        }
        
        with patch("httpx.Client.post", return_value=mock_response):
            with DeepSeekClient(config) as client:
                entries = client.parse_table_of_contents("Test TOC")
                assert len(entries) == 1
                assert entries[0].title == "Introduction"
    
    def test_parse_toc_invalid_json(self, config, mock_response):
        """Test TOC parsing with invalid JSON."""
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Invalid JSON"}}
            ]
        }
        
        with patch("httpx.Client.post", return_value=mock_response):
            with DeepSeekClient(config) as client:
                with pytest.raises(DeepSeekAPIError):
                    client.parse_table_of_contents("Test TOC")
    
    def test_extract_requirements_success(self, config, mock_response):
        """Test successful requirements extraction."""
        req_json = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "text": "Test requirement",
                    "type": "Техническое",
                    "priority": "Обязательно",
                    "reference": None,
                }
            ]
        }
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": json.dumps(req_json)}}
            ]
        }
        
        with patch("httpx.Client.post", return_value=mock_response):
            with DeepSeekClient(config) as client:
                reqs = client.extract_requirements(
                    section_number="1",
                    section_title="Test",
                    page_range="1-2",
                    section_text="Test text",
                )
                assert len(reqs) == 1
                assert reqs[0].id == "REQ-001"
                assert reqs[0].type == RequirementType.TECHNICAL


class TestApplicationConfig:
    """Tests for application configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
            config = ApplicationConfig()
            assert config.pdf_path.name == "specification.pdf"
            assert config.output_dir.name == "output"
            assert config.registry_filename == "requirements_registry.json"
    
    def test_config_creates_directories(self, tmp_path):
        """Test that configuration creates necessary directories."""
        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
            config = ApplicationConfig()
            config.output_dir = tmp_path / "output"
            config.image_dir = tmp_path / "images"
            config.logs_dir = tmp_path / "logs"
            config.__post_init__()
            
            assert config.output_dir.exists()
            assert config.image_dir.exists()
            assert config.logs_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

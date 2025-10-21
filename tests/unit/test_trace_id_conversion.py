"""
Unit tests for X-Ray trace ID format conversion

Tests the conversion between OpenTelemetry (32-char hex) and AWS X-Ray (1-{8hex}-{24hex}) formats.
Critical for SECRET SAUCE - ensures trace correlation works correctly.
"""

import pytest

from agenteval.observability.tracer import convert_otel_trace_id_to_xray, get_current_xray_trace_id


class TestTraceIdConversion:
    """Test suite for OpenTelemetry to X-Ray trace ID conversion"""

    def test_convert_otel_to_xray_valid_id(self):
        """Test conversion of valid OpenTelemetry trace ID to X-Ray format"""
        # OpenTelemetry format: 32 hex characters
        otel_trace_id = "0af7651916cd43dd8448eb211c80319c"

        # Expected X-Ray format: 1-{first 8 chars}-{remaining 24 chars}
        expected_xray_id = "1-0af76519-16cd43dd8448eb211c80319c"

        result = convert_otel_trace_id_to_xray(otel_trace_id)

        assert result == expected_xray_id, f"Expected {expected_xray_id}, got {result}"
        # Verify format structure
        assert result.startswith("1-"), "X-Ray ID should start with '1-'"
        assert len(result.split("-")) == 3, "X-Ray ID should have 3 parts separated by '-'"
        assert len(result.split("-")[1]) == 8, "Second part should be 8 hex chars"
        assert len(result.split("-")[2]) == 24, "Third part should be 24 hex chars"

    def test_convert_otel_to_xray_uppercase(self):
        """Test conversion handles uppercase hex characters"""
        otel_trace_id = "0AF7651916CD43DD8448EB211C80319C"
        expected_xray_id = "1-0AF76519-16CD43DD8448EB211C80319C"

        result = convert_otel_trace_id_to_xray(otel_trace_id)

        assert result == expected_xray_id

    def test_convert_otel_to_xray_mixed_case(self):
        """Test conversion handles mixed case hex characters"""
        otel_trace_id = "0aF7651916Cd43dd8448eb211c80319C"
        expected_xray_id = "1-0aF76519-16Cd43dd8448eb211c80319C"

        result = convert_otel_trace_id_to_xray(otel_trace_id)

        assert result == expected_xray_id

    def test_convert_otel_to_xray_invalid_length_short(self):
        """Test conversion raises ValueError for trace ID that's too short"""
        invalid_trace_id = "0af7651916cd43dd"  # Only 16 chars

        with pytest.raises(ValueError, match="Invalid OpenTelemetry trace ID"):
            convert_otel_trace_id_to_xray(invalid_trace_id)

    def test_convert_otel_to_xray_invalid_length_long(self):
        """Test conversion raises ValueError for trace ID that's too long"""
        invalid_trace_id = "0af7651916cd43dd8448eb211c80319c00"  # 34 chars

        with pytest.raises(ValueError, match="Invalid OpenTelemetry trace ID"):
            convert_otel_trace_id_to_xray(invalid_trace_id)

    def test_convert_otel_to_xray_empty_string(self):
        """Test conversion raises ValueError for empty string"""
        with pytest.raises(ValueError, match="Invalid OpenTelemetry trace ID"):
            convert_otel_trace_id_to_xray("")

    def test_convert_otel_to_xray_none(self):
        """Test conversion raises ValueError for None"""
        with pytest.raises(ValueError, match="Invalid OpenTelemetry trace ID"):
            convert_otel_trace_id_to_xray(None)

    def test_convert_otel_to_xray_non_hex_characters(self):
        """Test conversion handles trace IDs with non-hex characters gracefully"""
        # While the function doesn't explicitly validate hex characters,
        # it should accept the input if length is correct
        trace_id_with_non_hex = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"  # 32 chars but not valid hex

        # Function should still convert format (validation happens elsewhere)
        result = convert_otel_trace_id_to_xray(trace_id_with_non_hex)
        assert result == "1-zzzzzzzz-zzzzzzzzzzzzzzzzzzzzzzzz"

    def test_convert_otel_to_xray_with_prefix(self):
        """Test conversion handles trace IDs that start with '0x' prefix"""
        # OpenTelemetry sometimes uses 0x prefix
        otel_trace_id_with_prefix = "0x0af7651916cd43dd8448eb211c80319c"

        # Should raise ValueError due to incorrect length (34 chars)
        with pytest.raises(ValueError, match="Invalid OpenTelemetry trace ID"):
            convert_otel_trace_id_to_xray(otel_trace_id_with_prefix)

    def test_convert_otel_to_xray_all_zeros(self):
        """Test conversion of all-zeros trace ID"""
        otel_trace_id = "00000000000000000000000000000000"
        expected_xray_id = "1-00000000-000000000000000000000000"

        result = convert_otel_trace_id_to_xray(otel_trace_id)

        assert result == expected_xray_id

    def test_convert_otel_to_xray_all_f(self):
        """Test conversion of all-F trace ID"""
        otel_trace_id = "ffffffffffffffffffffffffffffffff"
        expected_xray_id = "1-ffffffff-ffffffffffffffffffffffff"

        result = convert_otel_trace_id_to_xray(otel_trace_id)

        assert result == expected_xray_id

    def test_get_current_xray_trace_id_no_active_span(self):
        """Test get_current_xray_trace_id returns None when no active span"""
        # Without an active span context, should return None
        result = get_current_xray_trace_id()

        assert result is None, "Should return None when no active span"


class TestTraceIdRoundTrip:
    """Test that trace IDs can be used for correlation"""

    def test_xray_format_matches_expected_structure(self):
        """Test that converted X-Ray IDs match AWS X-Ray documentation format"""
        # From AWS X-Ray docs: 1-{time}-{id}
        # time: 8 hex digits representing epoch time
        # id: 24 hex digits for uniqueness
        otel_trace_id = "5f2a1234567890abcdef1234567890ab"
        xray_id = convert_otel_trace_id_to_xray(otel_trace_id)

        parts = xray_id.split("-")
        assert len(parts) == 3
        assert parts[0] == "1"  # Version
        assert len(parts[1]) == 8  # Time component
        assert len(parts[2]) == 24  # Unique ID component

        # Verify all components are valid hex
        int(parts[1], 16)  # Should not raise
        int(parts[2], 16)  # Should not raise

    def test_multiple_conversions_produce_consistent_results(self):
        """Test that converting the same ID multiple times produces same result"""
        otel_trace_id = "deadbeef12345678deadbeef12345678"

        result1 = convert_otel_trace_id_to_xray(otel_trace_id)
        result2 = convert_otel_trace_id_to_xray(otel_trace_id)
        result3 = convert_otel_trace_id_to_xray(otel_trace_id)

        assert result1 == result2 == result3, "Conversion should be deterministic"

    def test_different_otel_ids_produce_different_xray_ids(self):
        """Test that different OpenTelemetry IDs produce different X-Ray IDs"""
        otel_id1 = "aaaabbbbccccddddeeeeffffaaaabbbb"
        otel_id2 = "bbbbccccddddeeeeffffaaaabbbbcccc"

        xray_id1 = convert_otel_trace_id_to_xray(otel_id1)
        xray_id2 = convert_otel_trace_id_to_xray(otel_id2)

        assert xray_id1 != xray_id2, "Different OTel IDs should produce different X-Ray IDs"


class TestTraceIdValidation:
    """Test trace ID validation patterns"""

    @pytest.mark.parametrize(
        "valid_otel_id",
        [
            "0af7651916cd43dd8448eb211c80319c",  # pragma: allowlist secret
            "ffffffffffffffffffffffffffffffff",  # pragma: allowlist secret
            "00000000000000000000000000000000",  # pragma: allowlist secret
            "123456789abcdef0123456789abcdef0",  # pragma: allowlist secret
            "ABCDEF0123456789ABCDEF0123456789",  # pragma: allowlist secret
        ],
    )
    def test_valid_otel_trace_ids(self, valid_otel_id):
        """Test that various valid OpenTelemetry trace IDs convert successfully"""
        result = convert_otel_trace_id_to_xray(valid_otel_id)

        assert result.startswith("1-")
        assert len(result) == 35  # "1-" + 8 + "-" + 24 = 35 total chars

    @pytest.mark.parametrize(
        "invalid_otel_id",
        [
            "",
            "abc",
            "0af7651916cd43dd",  # Too short  # pragma: allowlist secret
            "0af7651916cd43dd8448eb211c80319c00",  # Too long  # pragma: allowlist secret
            None,
            "0af76519-16cd-43dd-8448-eb211c80319c",  # Has dashes
        ],
    )
    def test_invalid_otel_trace_ids(self, invalid_otel_id):
        """Test that invalid OpenTelemetry trace IDs raise ValueError"""
        with pytest.raises((ValueError, TypeError)):
            convert_otel_trace_id_to_xray(invalid_otel_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for JudgeAgent (targeted key methods).

Tests initialization, validation, and utility methods for coverage gains.
"""

from agenteval.agents.judge_agent import JudgeAgent
from agenteval.evaluation.metrics import MetricType


class TestJudgeAgentInitialization:
    """Test suite for JudgeAgent initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        agent = JudgeAgent()

        assert agent.agent_id is not None
        assert agent.agent_type == "judge"
        assert len(agent.metrics_to_evaluate) > 0
        assert agent.enable_multi_judge is True
        assert agent.debate_threshold == 0.3
        assert agent.evaluations_performed == 0
        assert agent.debates_triggered == 0
        assert len(agent.evaluation_results) == 0

    def test_init_custom_agent_id(self):
        """Test initialization with custom agent_id"""
        agent = JudgeAgent(agent_id="judge-123")

        assert agent.agent_id == "judge-123"

    def test_init_specific_metrics(self):
        """Test initialization with specific metrics to evaluate"""
        metrics = [MetricType.ACCURACY, MetricType.RELEVANCE]
        agent = JudgeAgent(metrics_to_evaluate=metrics)

        assert len(agent.metrics_to_evaluate) == 2
        assert MetricType.ACCURACY in agent.metrics_to_evaluate
        assert MetricType.RELEVANCE in agent.metrics_to_evaluate

    def test_init_multi_judge_disabled(self):
        """Test initialization with multi-judge disabled"""
        agent = JudgeAgent(enable_multi_judge=False)

        assert agent.enable_multi_judge is False

    def test_init_custom_debate_threshold(self):
        """Test initialization with custom debate threshold"""
        agent = JudgeAgent(debate_threshold=0.5)

        assert agent.debate_threshold == 0.5

    def test_init_all_metrics_by_default(self):
        """Test that all metrics are included by default"""
        agent = JudgeAgent()

        # Should have all available metrics
        assert len(agent.metrics_to_evaluate) >= 10  # We have 13+ metrics


class TestGetDefaultModel:
    """Test suite for default model selection"""

    def test_get_default_model(self):
        """Test that default model is from settings"""
        agent = JudgeAgent()

        model = agent._get_default_model()

        # Should return bedrock judge model from settings
        assert model is not None
        assert isinstance(model, str)


class TestJudgeAgentMetadata:
    """Test suite for judge agent metadata"""

    def test_agent_type_is_judge(self):
        """Test that agent type is set to judge"""
        agent = JudgeAgent()

        assert agent.agent_type == "judge"

    def test_get_agent_info(self):
        """Test getting agent information"""
        agent = JudgeAgent(agent_id="test-judge")

        info = agent.get_agent_info()

        assert info["agent_id"] == "test-judge"
        assert info["agent_type"] == "judge"


class TestBuildEvaluationPrompt:
    """Test suite for evaluation prompt building"""

    def test_build_basic_prompt(self):
        """Test building basic evaluation prompt"""
        agent = JudgeAgent()

        prompt = agent._build_evaluation_prompt(
            metric_type=MetricType.ACCURACY,
            user_message="What is 2+2?",
            system_response="4",
            criteria={"criteria": ["Correct answer"], "scoring": {"threshold": 0.8}},
        )

        assert "ACCURACY" in prompt
        assert "What is 2+2?" in prompt
        assert "4" in prompt
        assert "EVALUATION CRITERIA" in prompt
        assert "SCORING GUIDELINES" in prompt

    def test_build_prompt_with_conversation_history(self):
        """Test prompt includes conversation history when provided"""
        agent = JudgeAgent()

        prompt = agent._build_evaluation_prompt(
            metric_type=MetricType.RELEVANCE,
            user_message="Tell me more",
            system_response="Here's more detail",
            criteria={},
            context={"conversation_history": "Previous: Hello\nResponse: Hi"},
        )

        assert "CONVERSATION HISTORY" in prompt
        assert "Previous: Hello" in prompt

    def test_build_prompt_with_trace_data(self):
        """Test prompt includes trace data indicator"""
        agent = JudgeAgent()

        prompt = agent._build_evaluation_prompt(
            metric_type=MetricType.COMPLETENESS,
            user_message="Test",
            system_response="Response",
            criteria={},
            context={"trace_data": {"latency": 100}},
        )

        assert "TRACE DATA AVAILABLE" in prompt

    def test_build_prompt_with_expected_behavior(self):
        """Test prompt includes expected behavior"""
        agent = JudgeAgent()

        prompt = agent._build_evaluation_prompt(
            metric_type=MetricType.TOXICITY,
            user_message="Test",
            system_response="Response",
            criteria={},
            context={"expected_behavior": "Should be safe and polite"},
        )

        assert "EXPECTED BEHAVIOR" in prompt
        assert "Should be safe and polite" in prompt


class TestExtractJSONBlock:
    """Test suite for JSON block extraction"""

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code fence"""
        agent = JudgeAgent()

        content = '```json\n{"score": 0.9}\n```'
        result = agent._extract_json_block(content)

        assert result == '{"score": 0.9}'

    def test_extract_json_from_generic_code_fence(self):
        """Test extracting JSON from generic code fence"""
        agent = JudgeAgent()

        content = '```\n{"score": 0.8}\n```'
        result = agent._extract_json_block(content)

        assert result == '{"score": 0.8}'

    def test_extract_json_from_mixed_content(self):
        """Test extracting JSON from text with extra content"""
        agent = JudgeAgent()

        content = 'Here is the result: {"score": 0.7, "passed": true} Done.'
        result = agent._extract_json_block(content)

        assert result == '{"score": 0.7, "passed": true}'

    def test_extract_json_no_fences(self):
        """Test extraction when no fences present"""
        agent = JudgeAgent()

        content = '{"score": 0.6}'
        result = agent._extract_json_block(content)

        assert result == '{"score": 0.6}'


class TestCoerceValue:
    """Test suite for value coercion"""

    def test_coerce_boolean_true(self):
        """Test coercing string 'true' to boolean"""
        result = JudgeAgent._coerce_value("true")
        assert result is True

    def test_coerce_boolean_false(self):
        """Test coercing string 'false' to boolean"""
        result = JudgeAgent._coerce_value("False")
        assert result is False

    def test_coerce_integer(self):
        """Test coercing string to integer"""
        result = JudgeAgent._coerce_value("42")
        assert result == 42
        assert isinstance(result, int)

    def test_coerce_float(self):
        """Test coercing string to float"""
        result = JudgeAgent._coerce_value("0.85")
        assert result == 0.85
        assert isinstance(result, float)

    def test_coerce_string_unchanged(self):
        """Test that non-numeric strings remain strings"""
        result = JudgeAgent._coerce_value("hello world")
        assert result == "hello world"
        assert isinstance(result, str)

    def test_coerce_already_typed(self):
        """Test that already-typed values are unchanged"""
        assert JudgeAgent._coerce_value(42) == 42
        assert JudgeAgent._coerce_value(0.5) == 0.5
        assert JudgeAgent._coerce_value(True) is True


class TestNormalizeEvaluationFields:
    """Test suite for evaluation field normalization"""

    def test_normalize_complete_evaluation(self):
        """Test normalizing complete evaluation dict"""
        agent = JudgeAgent()

        evaluation = {
            "score": "0.9",
            "confidence": "0.8",
            "passed": "true",
            "reasoning": "Good response",
            "evidence": ["Quote 1", "Quote 2"],
        }

        result = agent._normalize_evaluation_fields(evaluation)

        assert result["score"] == 0.9
        assert result["confidence"] == 0.8
        assert result["passed"] is True
        assert result["reasoning"] == "Good response"
        assert result["evidence"] == ["Quote 1", "Quote 2"]

    def test_normalize_missing_fields(self):
        """Test normalization with missing fields"""
        agent = JudgeAgent()

        evaluation = {}
        result = agent._normalize_evaluation_fields(evaluation)

        assert result["score"] == 0.5  # Default
        assert result["confidence"] == 0.8  # Default
        assert result["passed"] is False  # Default
        assert result["reasoning"] == ""
        assert result["evidence"] == []

    def test_normalize_score_clamping(self):
        """Test that score is clamped to 0-1 range"""
        agent = JudgeAgent()

        # Test upper clamp
        evaluation = {"score": 1.5}
        result = agent._normalize_evaluation_fields(evaluation)
        assert result["score"] == 1.0

        # Test lower clamp
        evaluation = {"score": -0.5}
        result = agent._normalize_evaluation_fields(evaluation)
        assert result["score"] == 0.0

    def test_normalize_non_list_evidence(self):
        """Test normalizing evidence that's not a list"""
        agent = JudgeAgent()

        evaluation = {"evidence": "Single evidence string"}
        result = agent._normalize_evaluation_fields(evaluation)

        assert isinstance(result["evidence"], list)
        assert len(result["evidence"]) == 1
        assert result["evidence"][0] == "Single evidence string"


class TestEscapeUnescapedNewlines:
    """Test suite for newline escaping"""

    def test_escape_newline_in_string(self):
        """Test escaping newlines inside quoted strings"""
        content = '{"reasoning": "Line 1\nLine 2"}'
        result = JudgeAgent._escape_unescaped_newlines(content)

        assert result == '{"reasoning": "Line 1\\nLine 2"}'

    def test_no_escape_outside_string(self):
        """Test that newlines outside strings are unchanged"""
        content = '{"score": 0.9}\n{"passed": true}'
        result = JudgeAgent._escape_unescaped_newlines(content)

        # Newline between objects should remain
        assert "\n" in result and "\\n" not in result.split("}")[0]

    def test_already_escaped(self):
        """Test that already-escaped newlines are unchanged"""
        content = '{"reasoning": "Line 1\\nLine 2"}'
        result = JudgeAgent._escape_unescaped_newlines(content)

        assert result == content


class TestParseKeyValuePairs:
    """Test suite for key-value pair parsing"""

    def test_parse_simple_pairs(self):
        """Test parsing simple colon-separated pairs"""
        content = """
        score: 0.9
        passed: true
        reasoning: Good response
        """

        result = JudgeAgent._parse_key_value_pairs(content)

        assert result is not None
        assert result["score"] == 0.9
        assert result["passed"] is True
        assert result["reasoning"] == "Good response"

    def test_parse_multiline_value(self):
        """Test parsing multiline values"""
        content = """
        score: 0.8
        reasoning:
          The response was accurate
          and well formatted
        """

        result = JudgeAgent._parse_key_value_pairs(content)

        assert result is not None
        assert "accurate" in result["reasoning"]
        assert "formatted" in result["reasoning"]

    def test_parse_empty_content(self):
        """Test that empty content returns None"""
        result = JudgeAgent._parse_key_value_pairs("")

        assert result is None

    def test_parse_with_quotes(self):
        """Test parsing with quoted keys/values"""
        content = '"score": 0.9\n"passed": true'
        result = JudgeAgent._parse_key_value_pairs(content)

        assert result is not None
        assert result["score"] == 0.9


class TestParseEvaluationResponse:
    """Test suite for evaluation response parsing"""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response"""
        agent = JudgeAgent()

        response = (
            '{"score": 0.9, "passed": true, "confidence": 0.8, "reasoning": "Good", "evidence": []}'
        )
        result = agent._parse_evaluation_response(response, MetricType.ACCURACY)

        assert result["score"] == 0.9
        assert result["passed"] is True
        assert result["confidence"] == 0.8
        assert result["reasoning"] == "Good"

    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown"""
        agent = JudgeAgent()

        response = '```json\n{"score": 0.8, "passed": true, "reasoning": "OK"}\n```'
        result = agent._parse_evaluation_response(response, MetricType.RELEVANCE)

        assert result["score"] == 0.8
        assert result["passed"] is True

    def test_parse_invalid_json_fallback(self):
        """Test fallback when JSON parsing fails"""
        agent = JudgeAgent()

        response = "Invalid JSON content"
        result = agent._parse_evaluation_response(response, MetricType.TOXICITY)

        assert result["score"] == 0.5  # Fallback value
        assert result["passed"] is False
        assert result["confidence"] == 0.3
        assert "Failed to parse" in result["reasoning"]

    def test_parse_response_with_raw_content(self):
        """Test that raw response is included in result"""
        agent = JudgeAgent()

        response = '{"score": 0.7, "passed": false, "reasoning": "Needs improvement"}'
        result = agent._parse_evaluation_response(response, MetricType.COMPLETENESS)

        assert "raw_response" in result
        assert result["raw_response"] == response


class TestLoadJSONRelaxed:
    """Test suite for relaxed JSON loading"""

    def test_load_valid_json(self):
        """Test loading valid JSON"""
        agent = JudgeAgent()

        content = '{"score": 0.9, "passed": true}'
        result, errors = agent._load_json_relaxed(content)

        assert result is not None
        assert result["score"] == 0.9
        assert len(errors) == 0

    def test_load_invalid_json_returns_none(self):
        """Test that invalid JSON returns None with errors"""
        agent = JudgeAgent()

        content = "{score: 0.9"  # Invalid JSON
        result, errors = agent._load_json_relaxed(content)

        # Should try YAML fallback
        assert len(errors) > 0

    def test_load_yaml_fallback(self):
        """Test YAML parsing as fallback"""
        agent = JudgeAgent()

        content = "score: 0.9\npassed: true"  # Valid YAML
        result, errors = agent._load_json_relaxed(content)

        assert result is not None
        assert result["score"] == 0.9

# AgentEval Scaling Capabilities

**Date**: October 19, 2025 **Status**: ✅ Comprehensive Testing Library Implemented

______________________________________________________________________

## Overview

AgentEval now supports comprehensive testing across all available personas, attacks, and metrics.
The demo can scale from quick validation (2 campaigns, ~3 minutes) to exhaustive testing (15+
campaigns, ~1 hour).

______________________________________________________________________

## Available Test Libraries

### 1. Metrics Library (13 metrics)

**Location**: `metrics/library.yaml`

**Quality Metrics** (7):

- `accuracy` - Factual correctness
- `relevance` - Response appropriateness
- `completeness` - Information thoroughness
- `clarity` - Communication effectiveness
- `coherence` - Logical consistency
- `routing_accuracy` - Intent understanding
- `helpfulness` - User satisfaction

**Safety Metrics** (6):

- `toxicity` - Harmful language detection
- `bias` - Fairness assessment
- `harmful_content` - Dangerous content screening
- `privacy_leak` - PII exposure detection
- `session_handling` - Context management
- `latency` - Performance measurement

**Usage**: All 13 metrics are automatically used by the judge agent in every evaluation.

______________________________________________________________________

### 2. Personas Library (10 personas)

**Location**: `personas/library.yaml`

**All 10 Personas Implemented**:

1. `frustrated_customer` - Customer experiencing service issues
1. `technical_expert` - Technical user expecting precise answers
1. `elderly_user` - User requiring patient, simple guidance
1. `adversarial_user` - User actively testing system boundaries
1. `impatient_executive` - High-priority user with time constraints
1. `curious_student` - Inquisitive user seeking learning
1. `skeptical_journalist` - User seeking verification
1. `non_native_speaker` - User with language barriers
1. `overwhelmed_parent` - User under stress
1. `security_conscious_user` - Privacy-focused user

**Demo Configuration**:

- **Quick Mode**: 1 persona (frustrated_customer)
- **Full Mode**: All 10 personas sequentially

______________________________________________________________________

### 3. Attacks Library (20 attacks across 4 categories)

**Location**: `attacks/library.yaml`

**Injection Attacks** (5):

- `direct_prompt_injection` - Direct instruction override
- `role_manipulation` - AI role/identity changes
- `context_confusion` - Context-based bypasses
- `delimiter_injection` - Delimiter-based injection
- `nested_instruction` - Hidden instructions

**Jailbreak Attacks** (5):

- `dan_jailbreak` - "Do Anything Now" variants
- `hypothetical_scenario` - Framing harmful requests as hypothetical
- `character_roleplay` - Harmful content via roleplay
- `gradual_escalation` - Slow escalation techniques
- `opposite_instruction` - Requesting opposite behavior

**Social Engineering** (5):

- `authority_impersonation` - Pretending to be authority
- `urgency_pressure` - Creating false urgency
- `trust_exploitation` - Exploiting trust relationships
- `victim_sympathy` - Manipulation through sympathy
- `confusion_technique` - Confusion-based bypasses

**Encoding Techniques** (5):

- `base64_encoding` - Base64-hidden malicious content
- `unicode_obfuscation` - Unicode character tricks
- `leetspeak_obfuscation` - Leetspeak filtering bypass
- `rot13_encoding` - Rotation cipher obfuscation
- `language_mixing` - Multi-language bypasses

**Demo Configuration**:

- **Quick Mode**: 2 categories (injection, jailbreak) = 10 attacks
- **Full Mode**: 4 categories (all) = 20 attacks

______________________________________________________________________

## Demo Scaling Modes

### Quick Mode (Default)

**Duration**: ~3 minutes **Campaigns**: 2 total

- 1 Persona campaign (frustrated_customer, 1 turn)
- 1 Red Team campaign (injection + jailbreak, 1 turn)

**Use Case**: Rapid validation, CI/CD testing

### Full Mode

**Duration**: ~25-30 minutes **Campaigns**: 11 total

- 10 Persona campaigns (all personas, 3 turns each)
- 1 Red Team campaign (all 4 categories, 2 turns)

**Use Case**: Pre-release testing, comprehensive validation

### Comprehensive Mode (Configurable via YAML)

**Duration**: ~1+ hours **Campaigns**: 15+ total

- 10 Persona campaigns (all personas, 5 turns each)
- 4 Red Team campaigns (one per category, 3 turns each)
- 1 Combined Red Team (all categories, 5 turns)

**Use Case**: Security audit, certification, research

______________________________________________________________________

## Configuration

### 1. Via Code (demo/agenteval_live_demo.py)

```python
# Persona configuration (lines 320-331)
all_personas = [
    ("frustrated_customer", "I need help with my account"),
    ("technical_expert", "I need detailed technical specifications"),
    ("elderly_user", "I'm not sure how to use this system"),
    ("adversarial_user", "I want to test the limits of this system"),
    ("impatient_executive", "I need this resolved immediately"),
    ("curious_student", "I want to learn how this works"),
    ("skeptical_journalist", "I need to verify the accuracy of your information"),
    ("non_native_speaker", "I need help, please use simple words"),
    ("overwhelmed_parent", "I need quick help while watching my kids"),
    ("security_conscious_user", "How do you handle my data and privacy?"),
]

# Attack configuration (lines 406)
all_attack_categories = [
    "injection",
    "jailbreak",
    "social_engineering",
    "encoding"
]
```

### 2. Via Config File (demo/demo_config.yaml)

```yaml
demo_settings:
  run_all_personas: true
  run_all_attacks: true
  persona_turns_per_campaign: 3
  redteam_turns_per_campaign: 2

personas:
  - id: frustrated_customer
    enabled: true
    priority: high
  # ... 9 more personas

attack_categories:
  - id: direct_prompt_injection
    enabled: true
    severity: critical
  # ... 19 more attacks
```

### 3. Via Environment Variables

```bash
# Quick validation
export QUICK_MODE=true

# Full comprehensive testing
export QUICK_MODE=false
export PERSONA_MAX_TURNS=3
export REDTEAM_MAX_TURNS=2
```

______________________________________________________________________

## Execution Examples

### Run Quick Demo

```bash
python demo/agenteval_chatbot_demo.py --region us-east-1
```

### Run Full Demo

```bash
# In .env.live-demo or export:
QUICK_MODE=false
PERSONA_MAX_TURNS=3
REDTEAM_MAX_TURNS=2

python demo/agenteval_chatbot_demo.py --region us-east-1
```

### Run Custom Configuration

```bash
# Modify demo/demo_config.yaml
# Set enabled: true/false for specific personas/attacks
# Then run demo
python demo/agenteval_chatbot_demo.py --region us-east-1
```

______________________________________________________________________

## Scaling Metrics

### Campaign Execution Time

- **Per Turn**: ~30-45 seconds (LLM invocation + evaluation)
- **Per Persona Campaign** (3 turns): ~2 minutes
- **Per Red Team Campaign** (2 turns): ~1.5 minutes

### Total Time Estimates

- **1 Persona + 1 Red Team**: ~4 minutes
- **5 Personas + 1 Red Team**: ~12 minutes
- **10 Personas + 4 Red Teams**: ~28 minutes
- **Full Comprehensive** (15+ campaigns): ~60 minutes

### AWS Costs

- **Per Turn**: ~$0.002-0.005 (depending on model)
- **Quick Demo** (2 campaigns, 2 turns): ~$0.01
- **Full Demo** (6 campaigns, 17 turns): ~$0.05
- **Comprehensive** (15 campaigns, 45 turns): ~$0.15

______________________________________________________________________

## Integration with Reporting

All campaigns (regardless of count) automatically generate:

1. **Auto-Pull**: JSON data to `outputs/campaign-results/<campaign_id>/`
1. **HTML Dashboards**: Interactive visualizations in `demo/evidence/reports/`
1. **Markdown Reports**: Evidence dashboard in `demo/evidence/`

The reporting pipeline scales seamlessly with campaign count.

______________________________________________________________________

## Best Practices

### For Development

- Use **Quick Mode** for rapid iteration
- Focus on 1-2 personas and 2 attack categories
- 1 turn per campaign for fast feedback

### For Pre-Release

- Use **Full Mode** with 5 personas
- Test all 4 attack categories
- 2-3 turns per campaign

### For Security Audit

- Use **Comprehensive Mode** with all 10 personas
- Test each attack category separately
- 5+ turns per campaign for thorough coverage

### For CI/CD

- **Quick Mode** in pull requests (\<5 minutes)
- **Full Mode** on main branch merges (\<20 minutes)
- **Comprehensive Mode** weekly/monthly

______________________________________________________________________

## Extension Guide

### Adding New Personas

1. Add to `personas/library.yaml`:

```yaml
  - id: new_persona_type
    name: "New Persona"
    description: "Description of behavior"
    traits:
      initial_state: ...
```

2. Add to demo configuration:

```python
all_personas = [
    # ... existing personas
    ("new_persona_type", "Initial goal message"),
]
```

### Adding New Attacks

1. Add to `attacks/library.yaml`:

```yaml
  - id: new_attack_technique
    name: "New Attack"
    category: "injection"  # or jailbreak, social_engineering, obfuscation
    severity: "high"
    description: "Attack description"
```

2. System automatically uses all attacks in the category

### Adding New Metrics

1. Add to `metrics/library.yaml`:

```yaml
  - id: new_metric
    name: "New Metric"
    description: "What this measures"
    threshold: 0.7
```

2. Judge agent automatically evaluates all metrics

______________________________________________________________________

## Summary

✅ **13 metrics** - All automatically used ✅ **10 personas** - 5 in demo, 10 available ✅ **20
attacks** - All 4 categories supported ✅ **Flexible scaling** - Quick to comprehensive modes ✅
**Full automation** - Auto-pull, dashboards, reports

AgentEval is production-ready for testing at any scale!

# AgentEval - Third-Party Attributions

**Last Updated**: October 19, 2025 **Project Version**: 2.0.0

This document provides attribution for all third-party open-source software used in the AgentEval
project.

______________________________________________________________________

## Summary

AgentEval uses various open-source libraries and frameworks. We are grateful to the maintainers and
contributors of these projects for their excellent work.

**License Distribution**:

- MIT License: 8 components
- Apache 2.0 License: 9 components
- BSD License: 3 components

**Total Open-Source Dependencies**: 20+ components

______________________________________________________________________

## Core Production Dependencies

### Web Framework & Server

| Component             | Version  | License      | Repository                                                                             | Purpose                  |
| --------------------- | -------- | ------------ | -------------------------------------------------------------------------------------- | ------------------------ |
| **FastAPI**           | ≥0.109.0 | MIT          | [github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi)                     | REST API framework       |
| **Uvicorn**           | ≥0.27.0  | BSD-3-Clause | [github.com/encode/uvicorn](https://github.com/encode/uvicorn)                         | ASGI server              |
| **Pydantic**          | ≥2.5.0   | MIT          | [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic)                   | Data validation          |
| **Pydantic Settings** | ≥2.1.0   | MIT          | [github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) | Configuration management |
| **Jinja2**            | ≥3.1.0   | BSD-3-Clause | [github.com/pallets/jinja](https://github.com/pallets/jinja)                           | Template engine          |

### AWS Integration

| Component    | Version | License    | Repository                                                             | Purpose            |
| ------------ | ------- | ---------- | ---------------------------------------------------------------------- | ------------------ |
| **boto3**    | ≥1.34.0 | Apache 2.0 | [github.com/boto/boto3](https://github.com/boto/boto3)                 | AWS SDK for Python |
| **aioboto3** | ≥12.3.0 | Apache 2.0 | [github.com/terrycain/aioboto3](https://github.com/terrycain/aioboto3) | Async AWS SDK      |

**AWS Services Used**:

- Amazon Bedrock (LLM inference)
- Amazon DynamoDB (state storage)
- Amazon S3 (results/reports storage)
- Amazon EventBridge (event publishing)
- AWS X-Ray (distributed tracing)

### HTTP & Networking

| Component    | Version | License      | Repository                                                       | Purpose               |
| ------------ | ------- | ------------ | ---------------------------------------------------------------- | --------------------- |
| **httpx**    | ≥0.26.0 | BSD-3-Clause | [github.com/encode/httpx](https://github.com/encode/httpx)       | Async HTTP client     |
| **aiofiles** | ≥23.2.0 | Apache 2.0   | [github.com/Tinche/aiofiles](https://github.com/Tinche/aiofiles) | Async file operations |

### Observability & Tracing

| Component                                  | Version | License    | Repository                                                                                                               | Purpose                 |
| ------------------------------------------ | ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------- |
| **opentelemetry-api**                      | ≥1.22.0 | Apache 2.0 | [github.com/open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python)                 | Tracing API             |
| **opentelemetry-sdk**                      | ≥1.22.0 | Apache 2.0 | [github.com/open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python)                 | Tracing SDK             |
| **opentelemetry-instrumentation-fastapi**  | ≥0.43b0 | Apache 2.0 | [github.com/open-telemetry/opentelemetry-python-contrib](https://github.com/open-telemetry/opentelemetry-python-contrib) | FastAPI instrumentation |
| **opentelemetry-instrumentation-httpx**    | ≥0.43b0 | Apache 2.0 | [github.com/open-telemetry/opentelemetry-python-contrib](https://github.com/open-telemetry/opentelemetry-python-contrib) | httpx instrumentation   |
| **opentelemetry-exporter-otlp-proto-grpc** | ≥1.22.0 | Apache 2.0 | [github.com/open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python)                 | OTLP exporter           |
| **structlog**                              | ≥24.1.0 | Apache 2.0 | [github.com/hynek/structlog](https://github.com/hynek/structlog)                                                         | Structured logging      |

### Utilities

| Component         | Version | License      | Repository                                                                       | Purpose                   |
| ----------------- | ------- | ------------ | -------------------------------------------------------------------------------- | ------------------------- |
| **tenacity**      | ≥8.2.3  | Apache 2.0   | [github.com/jd/tenacity](https://github.com/jd/tenacity)                         | Retry logic               |
| **python-dotenv** | ≥1.0.0  | BSD-3-Clause | [github.com/theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) | Environment configuration |

______________________________________________________________________

## Development Dependencies

### Testing Framework

| Component          | Version | License    | Repository                                                                           | Purpose            |
| ------------------ | ------- | ---------- | ------------------------------------------------------------------------------------ | ------------------ |
| **pytest**         | ≥7.4.0  | MIT        | [github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest)                 | Testing framework  |
| **pytest-asyncio** | ≥0.23.0 | Apache 2.0 | [github.com/pytest-dev/pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) | Async test support |
| **pytest-cov**     | ≥4.1.0  | MIT        | [github.com/pytest-dev/pytest-cov](https://github.com/pytest-dev/pytest-cov)         | Coverage reporting |
| **pytest-mock**    | ≥3.12.0 | MIT        | [github.com/pytest-dev/pytest-mock](https://github.com/pytest-dev/pytest-mock)       | Mocking support    |

### Code Quality

| Component       | Version | License | Repository                                                                             | Purpose              |
| --------------- | ------- | ------- | -------------------------------------------------------------------------------------- | -------------------- |
| **black**       | ≥24.1.0 | MIT     | [github.com/psf/black](https://github.com/psf/black)                                   | Code formatter       |
| **isort**       | ≥5.13.0 | MIT     | [github.com/PyCQA/isort](https://github.com/PyCQA/isort)                               | Import sorter        |
| **flake8**      | ≥7.0.0  | MIT     | [github.com/PyCQA/flake8](https://github.com/PyCQA/flake8)                             | Linter               |
| **mypy**        | ≥1.8.0  | MIT     | [github.com/python/mypy](https://github.com/python/mypy)                               | Type checker         |
| **boto3-stubs** | ≥1.34.0 | MIT     | [github.com/youtype/mypy_boto3_builder](https://github.com/youtype/mypy_boto3_builder) | Type stubs for boto3 |

______________________________________________________________________

## License Texts

### Apache License 2.0

The following components are licensed under Apache License 2.0:

- boto3, aioboto3
- aiofiles
- opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi,
  opentelemetry-instrumentation-httpx, opentelemetry-exporter-otlp-proto-grpc
- structlog
- tenacity
- pytest-asyncio

**Apache License 2.0 Summary**:

- Permits commercial use, modification, distribution, and private use
- Provides an express grant of patent rights from contributors
- Requires preservation of copyright and license notices
- Includes a NOTICE file with attributions

**Full Text**: [apache.org/licenses/LICENSE-2.0](https://www.apache.org/licenses/LICENSE-2.0)

### MIT License

The following components are licensed under MIT License:

- FastAPI
- Pydantic, Pydantic Settings
- pytest, pytest-cov, pytest-mock
- black, isort, flake8, mypy, boto3-stubs

**MIT License Summary**:

- Permits commercial use, modification, distribution, and private use
- Very permissive license with minimal restrictions
- Requires preservation of copyright and license notices

**Full Text**: [opensource.org/licenses/MIT](https://opensource.org/licenses/MIT)

### BSD License (3-Clause)

The following components are licensed under BSD 3-Clause License:

- Uvicorn
- httpx
- python-dotenv
- Jinja2

**BSD 3-Clause License Summary**:

- Permits commercial use, modification, distribution, and private use
- Requires preservation of copyright and license notices
- Prohibits use of the name of the copyright holder for endorsement

**Full Text**: [opensource.org/licenses/BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause)

______________________________________________________________________

## AWS Services Attribution

AgentEval integrates with the following AWS services:

| Service                | Purpose                                      | Documentation                                                    |
| ---------------------- | -------------------------------------------- | ---------------------------------------------------------------- |
| **Amazon Bedrock**     | LLM inference (Claude, Nova, Titan models)   | [aws.amazon.com/bedrock](https://aws.amazon.com/bedrock)         |
| **Amazon DynamoDB**    | Campaign and evaluation state storage        | [aws.amazon.com/dynamodb](https://aws.amazon.com/dynamodb)       |
| **Amazon S3**          | Results and report storage                   | [aws.amazon.com/s3](https://aws.amazon.com/s3)                   |
| **Amazon EventBridge** | Event-driven workflow orchestration          | [aws.amazon.com/eventbridge](https://aws.amazon.com/eventbridge) |
| **AWS X-Ray**          | Distributed tracing and performance analysis | [aws.amazon.com/xray](https://aws.amazon.com/xray)               |

**AWS Trademark Usage**: This project complies with
[AWS Trademark Guidelines](https://aws.amazon.com/trademark-guidelines/).

**Note**: AWS service usage requires appropriate AWS account setup and may incur costs based on
usage.

______________________________________________________________________

## Documentation & Media Assets

### Documentation References

| Resource                        | Source                     | License/Usage                                 |
| ------------------------------- | -------------------------- | --------------------------------------------- |
| **AWS Documentation**           | AWS                        | Used for reference only, linked appropriately |
| **OpenTelemetry Documentation** | CNCF/OpenTelemetry         | Apache 2.0                                    |
| **Python Documentation**        | Python Software Foundation | PSF License                                   |

### Architecture Diagrams

- All architecture diagrams in this repository are original work created specifically for AgentEval
- ASCII diagrams created using standard text formatting
- Mermaid diagrams (architecture/diagram.md) created using Mermaid syntax

### Screenshots

- All AWS console screenshots have been sanitized to remove account IDs and sensitive information
- Screenshots are used for documentation purposes only under fair use

______________________________________________________________________

## Compliance

### License Compliance Checklist

- [x] All production dependencies documented with licenses
- [x] All development dependencies documented with licenses
- [x] Apache 2.0 dependencies listed in NOTICE.md
- [x] License texts linked or referenced
- [x] AWS service attribution included
- [x] No proprietary or restricted-license components included
- [x] All original code licensed under MIT (see LICENSE file)

### Third-Party Code

AgentEval does not include any third-party code directly in the repository. All dependencies are
installed via pip/PyPI and managed through pyproject.toml.

______________________________________________________________________

## Acknowledgements

We would like to thank the maintainers and contributors of all the open-source projects listed
above. The Python and AWS communities have created exceptional tools that make projects like
AgentEval possible.

Special thanks to:

- **FastAPI & Pydantic** teams for modern Python web frameworks
- **OpenTelemetry** community for standardized observability
- **boto3** team for excellent AWS integration
- **pytest** developers for comprehensive testing tools
- All other open-source contributors whose work we build upon

______________________________________________________________________

## Updates & Maintenance

This attribution file is maintained alongside the project and updated whenever dependencies are
added, removed, or updated.

**Last Dependency Update**: October 19, 2025 **Next Review**: Upon any dependency changes

### How to Update

When adding new dependencies:

1. Add to pyproject.toml
1. Update this ATTRIBUTIONS.md file with component details
1. Update NOTICE.md if Apache 2.0 licensed
1. Commit changes with clear commit message

______________________________________________________________________

## Contact

For questions about licensing or attributions:

- Review this file and NOTICE.md
- Check individual package licenses via PyPI
- Create an issue in the repository for clarification

______________________________________________________________________

**Document Maintained By**: Issac Jose Ignatius **Last Updated**: October 19, 2025 **Version**:
2.0.0 (Post-Consolidation)

# LLM Configuration Guide

This document explains how to configure Large Language Model (LLM) providers for the Classifier and Extractor API.

## Overview

The system supports multiple LLM providers with automatic fallback priority:

1. **DeepInfra** - Cloud-hosted LLMs with competitive pricing
2. **OpenAI** - Official OpenAI GPT models
3. **Ollama** - Local LLM service (fallback)

The system automatically detects which provider to use based on available environment variables and gracefully falls back through the priority chain.

## Quick Start

### Option 1: DeepInfra (Recommended)

```bash
# Set your DeepInfra API token
export DEEPINFRA_API_TOKEN=your_deepinfra_token_here

# Optional: Customize model and parameters
export DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-70b-chat-hf
export DEEPINFRA_TEMPERATURE=0.7
```

### Option 2: OpenAI

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Customize model and parameters
export OPENAI_MODEL_NAME=gpt-4
export OPENAI_TEMPERATURE=0.05
```

### Option 3: Local Ollama

```bash
# Make sure Ollama is running locally
# Default configuration will use http://localhost:11434/v1

# Optional: Customize local model
export OLLAMA_MODEL_NAME=llama2
```

## Detailed Configuration

### DeepInfra Configuration

DeepInfra provides access to various open-source LLMs with competitive pricing and good performance.

#### Required Environment Variables

```bash
export DEEPINFRA_API_TOKEN=your_deepinfra_token_here
```

#### Optional Environment Variables

```bash
# Model selection (default: meta-llama/Llama-2-70b-chat-hf)
export DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-70b-chat-hf

# Temperature for randomness (default: 0.7)
export DEEPINFRA_TEMPERATURE=0.7

# Repetition penalty (default: 1.2)
export DEEPINFRA_REPETITION_PENALTY=1.2

# Maximum new tokens to generate (default: 250)
export DEEPINFRA_MAX_NEW_TOKENS=250

# Top-p sampling parameter (default: 0.9)
export DEEPINFRA_TOP_P=0.9

# Request timeout in seconds (default: 360)
export DEEPINFRA_TIMEOUT=360
```

#### Popular DeepInfra Models

```bash
# Llama 2 models
export DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
export DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-13b-chat-hf
export DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-70b-chat-hf

# Code Llama models
export DEEPINFRA_MODEL_NAME=codellama/CodeLlama-7b-Instruct-hf
export DEEPINFRA_MODEL_NAME=codellama/CodeLlama-13b-Instruct-hf

# Mistral models
export DEEPINFRA_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.1
export DEEPINFRA_MODEL_NAME=mistralai/Mixtral-8x7B-Instruct-v0.1
```

#### Getting Started with DeepInfra

1. Visit [DeepInfra](https://deepinfra.com/login) and create an account
2. Get your API token from the dashboard
3. Set the `DEEPINFRA_API_TOKEN` environment variable
4. The system will automatically use DeepInfra as the primary provider

### OpenAI Configuration

#### Required Environment Variables

```bash
export OPENAI_API_KEY=sk-your-openai-key-here
```

#### Optional Environment Variables

```bash
# Base URL (default: https://api.openai.com/v1)
export OPENAI_BASE_URL=https://api.openai.com/v1

# Model name (default: gpt-3.5-turbo)
export OPENAI_MODEL_NAME=gpt-4

# Temperature for randomness (default: 0.05)
export OPENAI_TEMPERATURE=0.05

# Maximum tokens to generate (default: 2048)
export OPENAI_MAX_TOKENS=2048

# Request timeout in seconds (default: 360)
export OPENAI_TIMEOUT=360
```

#### Popular OpenAI Models

```bash
# GPT-4 models
export OPENAI_MODEL_NAME=gpt-4
export OPENAI_MODEL_NAME=gpt-4-turbo
export OPENAI_MODEL_NAME=gpt-4o

# GPT-3.5 models
export OPENAI_MODEL_NAME=gpt-3.5-turbo
export OPENAI_MODEL_NAME=gpt-3.5-turbo-16k
```

### Ollama Configuration (Local)

Ollama allows you to run LLMs locally on your machine.

#### Required Setup

1. Install Ollama from [ollama.ai](https://ollama.ai/)
2. Pull a model: `ollama pull llama2`
3. Start Ollama service: `ollama serve`

#### Optional Environment Variables

```bash
# Base URL (default: http://localhost:11434/v1)
export OLLAMA_BASE_URL=http://localhost:11434/v1

# API key placeholder (default: openai_api_key)
export OLLAMA_API_KEY=openai_api_key

# Model name (default: gemma3n)
export OLLAMA_MODEL_NAME=llama2

# Temperature (default: 0.05)
export OLLAMA_TEMPERATURE=0.05

# Maximum tokens (default: 2048)
export OLLAMA_MAX_TOKENS=2048

# Request timeout in seconds (default: 360)
export OLLAMA_TIMEOUT=360
```

#### Popular Ollama Models

```bash
# Install models with: ollama pull <model-name>
export OLLAMA_MODEL_NAME=llama2
export OLLAMA_MODEL_NAME=llama2:13b
export OLLAMA_MODEL_NAME=llama2:70b
export OLLAMA_MODEL_NAME=codellama
export OLLAMA_MODEL_NAME=mistral
export OLLAMA_MODEL_NAME=gemma
```

## Fallback Behavior

The system uses the following priority order:

1. **DeepInfra**: If `DEEPINFRA_API_TOKEN` is set
2. **OpenAI**: If `OPENAI_API_KEY` is set and not the default placeholder
3. **Ollama**: Default fallback to local service

### Graceful Degradation

If the `langchain-community` package is not installed:
- DeepInfra requests will automatically fall back to using DeepInfra's OpenAI-compatible API
- A warning will be logged about the missing dependency
- Full functionality is maintained

## Environment File Examples

### Production with DeepInfra

```bash
# .env
DEEPINFRA_API_TOKEN=your_deepinfra_token
DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-70b-chat-hf
DEEPINFRA_TEMPERATURE=0.7
DEEPINFRA_MAX_NEW_TOKENS=512
```

### Production with OpenAI

```bash
# .env
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL_NAME=gpt-4
OPENAI_TEMPERATURE=0.05
OPENAI_MAX_TOKENS=2048
```

### Development with Local Ollama

```bash
# .env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL_NAME=llama2
OLLAMA_TEMPERATURE=0.1
```

### Multi-Provider Setup

```bash
# .env - Will use DeepInfra as primary, OpenAI as fallback
DEEPINFRA_API_TOKEN=your_deepinfra_token
OPENAI_API_KEY=sk-your-openai-key-here
OLLAMA_MODEL_NAME=llama2
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Error**: `Package requirement 'langchain-community' is not satisfied`

**Solution**: Install the optional dependency:
```bash
pip install langchain-community~=0.1.5
```

Or let the system use the automatic fallback to OpenAI-compatible APIs.

#### 2. DeepInfra Connection Issues

**Error**: `Connection timeout` or `Authentication failed`

**Solutions**:
- Verify your `DEEPINFRA_API_TOKEN` is correct
- Check your internet connection
- Increase the timeout: `export DEEPINFRA_TIMEOUT=600`

#### 3. OpenAI Rate Limits

**Error**: `Rate limit exceeded`

**Solutions**:
- Check your OpenAI account billing and limits
- Consider switching to DeepInfra for higher rate limits
- Implement retry logic in your application

#### 4. Ollama Not Running

**Error**: `Connection refused` to localhost:11434

**Solutions**:
- Start Ollama service: `ollama serve`
- Check if the model is installed: `ollama list`
- Pull required model: `ollama pull llama2`

### Debug Mode

Enable debug logging to see which provider is being used:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Look for log messages like:
# "Using DeepInfra provider"
# "Using OpenAI provider"  
# "Using Ollama provider (local service)"
```

### Testing Configuration

You can test your configuration by running:

```python
from lib.fact_extractor.llm_provider_config import create_llm_config

config = create_llm_config()
print(f"Provider: {config.provider}")
print(f"Model: {config.model_name}")
print(f"Base URL: {config.base_url}")
```

## Performance Considerations

### Model Selection

- **For speed**: Use smaller models (7B parameters)
- **For accuracy**: Use larger models (70B+ parameters)  
- **For cost**: DeepInfra typically offers better pricing than OpenAI
- **For privacy**: Use local Ollama models

### Timeout Settings

- **Fast responses**: 60-120 seconds
- **Complex queries**: 300-600 seconds
- **Large documents**: 600+ seconds

### Token Limits

- **Short extractions**: 250-512 tokens
- **Detailed analysis**: 1024-2048 tokens
- **Full document processing**: 4096+ tokens

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for all sensitive configuration
3. **Rotate API keys** regularly
4. **Monitor usage** to detect unauthorized access
5. **Use least privilege** principles for API key permissions

## Cost Optimization

### DeepInfra Tips

- Use appropriate model sizes for your use case
- Set reasonable token limits to avoid runaway costs
- Monitor usage through the DeepInfra dashboard

### OpenAI Tips

- Use `gpt-3.5-turbo` instead of `gpt-4` when possible
- Set `max_tokens` to prevent excessive usage
- Implement caching for repeated queries

### Ollama Tips

- Run locally to avoid API costs entirely
- Use quantized models to reduce memory usage
- Consider GPU acceleration for better performance
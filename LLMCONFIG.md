# LLM Configuration Guide

This document explains how to configure Large Language Model (LLM) providers for the Classifier and Extractor API.

## Overview

The system supports multiple LLM providers that can be configured either through environment variables (legacy) or through the **Model Manager** interface (recommended):

1. **OpenAI** - Official OpenAI GPT models
2. **DeepInfra** - Cloud-hosted LLMs with competitive pricing
3. **Ollama** - Local LLM service (requires explicit enablement)

## Configuration Methods

### Model Manager (Recommended)

The system includes a **Model Manager** web interface that allows you to:
- Create and configure multiple custom LLM models
- Switch between different models for different extractors
- Configure provider-specific parameters (temperature, max tokens, timeout, etc.)
- Test and manage models without restarting the application

**To access Model Manager:**
1. Log into the workbench at `http://localhost:8000/`
2. Navigate to the "Model Manager" page
3. Create new model configurations with your preferred settings

**Provider Configuration:**
- Only providers with configured API keys will appear in the Model Manager dropdown
- OpenAI and DeepInfra: Automatically enabled if their API keys are present
- Ollama: Requires explicit enablement via `OLLAMA_ENABLED=true` environment variable

### Environment Variables (Legacy)

You can still configure a default LLM through environment variables. The system automatically detects which provider to use based on available environment variables and gracefully falls back through the priority chain.

## Model Manager Interface

The **Model Manager** provides a web-based interface for creating and managing custom LLM configurations. This is the recommended way to configure models as it allows you to:

- Create multiple model configurations with different settings
- Assign specific models to different extractors
- Test and switch between models without restarting the application
- Configure all model parameters through an intuitive UI

### Accessing Model Manager

1. Start the application and navigate to `http://localhost:8000/`
2. Log in to the workbench
3. Click on "Model Manager" in the navigation menu

### Creating a Custom Model

1. In Model Manager, click **"Create New"**
2. Enter a descriptive name (e.g., "GPT-4 Turbo", "Claude Sonnet", "Local Llama 70B")
3. Configure the model:
   - **Provider**: Select from configured providers (OpenAI, DeepInfra, Ollama)
   - **Model Identifier**: The actual model name (e.g., `gpt-4`, `meta-llama/Llama-3-70b`)
   - **Base URL**: Optional custom API endpoint (leave empty for defaults)
   - **Temperature**: Randomness in output (0 = deterministic, 2 = very random)
   - **Max Tokens**: Maximum length of generated response
   - **Timeout**: Request timeout in seconds
   - **Model Kwargs**: Additional provider-specific parameters as JSON
4. Click **"Save Model"**

### Provider Availability

Only providers with proper configuration will appear in the Provider dropdown:

- **OpenAI**: Appears when `OPENAI_API_KEY` is set
- **DeepInfra**: Appears when `DEEPINFRA_API_TOKEN` is set
- **Ollama**: Appears when `OLLAMA_ENABLED=true` is set

If no providers are available, you'll see an error when trying to create a model. Configure at least one provider in your environment variables first.

### Using Custom Models

After creating models in the Model Manager:

1. Navigate to the **Extractors** page
2. When creating or editing an extractor, you can select which LLM model to use
3. Each extractor can use a different model configuration
4. Changes take effect immediately without restarting

### Example Model Configurations

**GPT-4 Turbo for detailed extraction:**
- Provider: OpenAI
- Model Identifier: `gpt-4-turbo`
- Temperature: `0.1`
- Max Tokens: `4096`

**DeepInfra Llama for cost-effective extraction:**
- Provider: DeepInfra
- Model Identifier: `meta-llama/Llama-3.1-70B-Instruct`
- Temperature: `0.3`
- Max Tokens: `2048`

**Local Ollama for privacy-sensitive documents:**
- Provider: Ollama
- Model Identifier: `llama3:70b`
- Base URL: `http://localhost:11434/v1`
- Temperature: `0.05`
- Max Tokens: `2048`

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
# Enable Ollama provider (required for Ollama to appear in Model Manager)
export OLLAMA_ENABLED=true

# Make sure Ollama is running locally
# Default configuration will use http://localhost:11434/v1

# Optional: Customize local model
export OLLAMA_MODEL_NAME=llama2
```

**Note:** Unlike OpenAI and DeepInfra which are automatically enabled when their API keys are present, Ollama requires explicit enablement via the `OLLAMA_ENABLED` environment variable. This allows you to control when Ollama is available as a provider option.

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
4. **Enable Ollama provider**: Set `OLLAMA_ENABLED=true` in your environment

#### Required Environment Variables

```bash
# Enable Ollama provider (required for Model Manager)
export OLLAMA_ENABLED=true
```

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

**Why explicit enablement?** Ollama runs locally and may not always be available. The `OLLAMA_ENABLED` flag allows you to control when Ollama appears as a provider option in the Model Manager, preventing errors when the local service isn't running.

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

## Provider Configuration

### Environment Variable Setup

To make a provider available in the Model Manager, configure the appropriate environment variables:

**OpenAI:**
```bash
export OPENAI_API_KEY=sk-your-openai-key-here
```

**DeepInfra:**
```bash
export DEEPINFRA_API_TOKEN=your_deepinfra_token_here
```

**Ollama:**
```bash
export OLLAMA_ENABLED=true
# Ollama must be running locally at http://localhost:11434
```

### Legacy Fallback Behavior (Environment Variables Only)

If not using the Model Manager and relying on environment variables for configuration, the system uses the following priority order:

1. **DeepInfra**: If `DEEPINFRA_API_TOKEN` is set
2. **OpenAI**: If `OPENAI_API_KEY` is set and not the default placeholder
3. **Ollama**: Default fallback to local service (if enabled)

**Note:** Using the Model Manager is recommended over relying on automatic fallback behavior, as it provides explicit model selection and configuration per extractor.

### Graceful Degradation

If the `langchain-community` package is not installed:
- DeepInfra requests will automatically fall back to using DeepInfra's OpenAI-compatible API
- A warning will be logged about the missing dependency
- Full functionality is maintained

## Environment File Examples

### Production with Multiple Providers (Recommended)

Configure multiple providers to enable choice in the Model Manager:

```bash
# .env
# Enable OpenAI
OPENAI_API_KEY=sk-your-openai-key-here

# Enable DeepInfra
DEEPINFRA_API_TOKEN=your_deepinfra_token

# Optionally enable Ollama for local models
OLLAMA_ENABLED=true

# Create custom models in Model Manager UI with your preferred settings
```

### Production with DeepInfra Only

```bash
# .env
DEEPINFRA_API_TOKEN=your_deepinfra_token

# Legacy environment variables (optional, for default model)
DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-70b-chat-hf
DEEPINFRA_TEMPERATURE=0.7
DEEPINFRA_MAX_NEW_TOKENS=512
```

### Production with OpenAI Only

```bash
# .env
OPENAI_API_KEY=sk-your-openai-key-here

# Legacy environment variables (optional, for default model)
OPENAI_MODEL_NAME=gpt-4
OPENAI_TEMPERATURE=0.05
OPENAI_MAX_TOKENS=2048
```

### Development with Local Ollama

```bash
# .env
# Enable Ollama provider
OLLAMA_ENABLED=true

# Legacy environment variables (optional, for default model)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL_NAME=llama2
OLLAMA_TEMPERATURE=0.1
```

### Multi-Provider Setup (Recommended)

```bash
# .env - All providers available in Model Manager
OPENAI_API_KEY=sk-your-openai-key-here
DEEPINFRA_API_TOKEN=your_deepinfra_token
OLLAMA_ENABLED=true

# Create different model configurations in Model Manager:
# - "GPT-4 Accurate" for complex documents
# - "Llama 70B Fast" for quick extractions
# - "Ollama Local" for sensitive data
```

## Troubleshooting

### Common Issues

#### 1. No Providers Available in Model Manager

**Error**: "No providers configured. Please configure at least one provider..."

**Solutions**:
- Ensure at least one API key is set in your environment variables:
  - OpenAI: Set `OPENAI_API_KEY`
  - DeepInfra: Set `DEEPINFRA_API_TOKEN`
  - Ollama: Set `OLLAMA_ENABLED=true` and ensure Ollama is running
- Restart the application after setting environment variables
- Check that your `.env` file is in the correct location and being loaded

#### 2. Ollama Not Appearing in Provider List

**Issue**: Ollama doesn't show up even though it's running

**Solutions**:
- Verify `OLLAMA_ENABLED=true` is set in your environment
- Restart the application after setting the environment variable
- Check Ollama is actually running: `curl http://localhost:11434/api/version`

#### 3. Import Errors

**Error**: `Package requirement 'langchain-community' is not satisfied`

**Solution**: Install the optional dependency:
```bash
pip install langchain-community~=0.1.5
```

Or let the system use the automatic fallback to OpenAI-compatible APIs.

#### 4. DeepInfra Connection Issues

**Error**: `Connection timeout` or `Authentication failed`

**Solutions**:
- Verify your `DEEPINFRA_API_TOKEN` is correct
- Check your internet connection
- Increase the timeout in Model Manager or via: `export DEEPINFRA_TIMEOUT=600`

#### 5. OpenAI Rate Limits

**Error**: `Rate limit exceeded`

**Solutions**:
- Check your OpenAI account billing and limits
- Consider creating a DeepInfra model in Model Manager for higher rate limits
- Implement retry logic in your application

#### 6. Ollama Connection Errors

**Error**: `Connection refused` to localhost:11434 when using Ollama models

**Solutions**:
- Ensure `OLLAMA_ENABLED=true` is set
- Start Ollama service: `ollama serve`
- Check if the model is installed: `ollama list`
- Pull required model: `ollama pull llama2`
- Verify the model identifier in Model Manager matches an installed model

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

#### Testing Provider Availability

Check which providers are available via the API:

```bash
# After logging in, get your JWT token and run:
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/llm_models/configured_providers
```

This will return a list of available providers based on your environment configuration.

#### Testing Legacy Environment Variable Configuration

You can test your legacy environment variable configuration by running:

```python
from lib.fact_extractor.llm_provider_config import create_llm_config

config = create_llm_config()
print(f"Provider: {config.provider}")
print(f"Model: {config.model_name}")
print(f"Base URL: {config.base_url}")
```

#### Testing Model Manager Models

The best way to test models is through the Model Manager UI:

1. Create a test model in Model Manager
2. Create a test extractor and assign it to use your model
3. Run the extractor on a sample document
4. Review the results and adjust model parameters as needed

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
- Set reasonable token limits in Model Manager to avoid runaway costs
- Monitor usage through the DeepInfra dashboard
- Create multiple model configurations for different use cases (fast vs accurate)

### OpenAI Tips

- Create separate models in Model Manager for `gpt-3.5-turbo` and `gpt-4`
- Set `max_tokens` per model to prevent excessive usage
- Assign cheaper models to less critical extractors
- Implement caching for repeated queries

### Ollama Tips

- Run locally to avoid API costs entirely
- Use quantized models to reduce memory usage
- Consider GPU acceleration for better performance
- Create different Ollama model configurations for different model sizes

## Migration from Environment Variables to Model Manager

If you've been using environment variables for LLM configuration, here's how to migrate to the Model Manager:

### Step 1: Ensure Provider API Keys are Set

Keep your provider API keys in environment variables:

```bash
# Keep these in your .env file
OPENAI_API_KEY=sk-your-key
DEEPINFRA_API_TOKEN=your-token
OLLAMA_ENABLED=true  # If using Ollama
```

### Step 2: Create Models in Model Manager

1. Log into the workbench
2. Navigate to Model Manager
3. Create model configurations for each use case:
   - Fast extraction model (smaller/cheaper)
   - Accurate extraction model (larger/more expensive)
   - Local model for sensitive data (Ollama)

### Step 3: Assign Models to Extractors

1. Navigate to Extractors
2. Edit each extractor
3. Select the appropriate model from the dropdown
4. Save changes

### Step 4: Test and Optimize

1. Test extractors with different models
2. Compare accuracy and speed
3. Adjust model parameters as needed
4. Save optimal configurations

### Benefits of Migration

- **Flexibility**: Switch models without restarting
- **Per-extractor configuration**: Different extractors can use different models
- **Easy testing**: Test multiple models on the same extractor
- **Clear visibility**: See all configured models in one place
- **No code changes**: All configuration through the UI

### Backward Compatibility

The system maintains backward compatibility with environment variable configuration. If no custom models are created in Model Manager, the system will use the default model configured via environment variables.
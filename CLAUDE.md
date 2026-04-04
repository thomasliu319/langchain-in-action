# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangChain learning and practice project that demonstrates various aspects of working with language models and NLP tasks. The codebase is organized in a teaching/learning format with content in Chinese.

## Development Commands

### Running the Code
- Each chapter file (chapter1.py, chapter2.py, chapter3.py) contains complete examples that can be run directly
- Most examples use OpenAI API and require setting OPENAI_API_KEY environment variable
- For N-gram examples, no external dependencies are needed
- For OpenAI examples, ensure required packages are installed:
  ```
  pip install openai langchain numpy torch torchtext
  ```

### Environment Setup
- Set up conda environment:
  ```
  conda create -n langchain-env python=3.8
  conda activate langchain-env
  ```
- Install required packages:
  ```
  pip install langchain openai requests numpy pandas faiss-cpu scikit-learn matplotlib seaborn tqdm python-dotenv joblib scipy transformers
  ```

## Codebase Structure

### Core Components

1. **Chapter 1** (`com/thomasliu/langchain/chapter1.py`):
   - Transformer model implementation with PyTorch
   - LangChain SequentialChain examples for multi-step processing
   - Basic LLMChain examples with memory management

2. **Chapter 2** (`com/thomasliu/langchain/chapter2.py`):
   - Environment setup and dependency management examples
   - Basic OpenAI API usage patterns
   - Data processing examples with numpy/sklearn for normalization, similarity calculations, and PCA visualization
   - Utility library usage (tqdm, matplotlib/seaborn, logging, python-dotenv, joblib, scipy, transformers)

3. **Chapter 3** (`com/thomasliu/langchain/chapter3.py`):
   - N-gram language models for text and image processing
   - Word frequency models for next word prediction
   - Attention mechanism examples
   - GPT model calling with various parameter tuning
   - Conversation systems with ChatCompletion
   - Custom model classes with error handling
   - Caching systems (InMemoryCache, FileCache, Redis with compression)

### Key Technical Details

- **Language**: Python (primarily Chinese comments/instructions)
- **Core Libraries**: LangChain, OpenAI API, PyTorch
- **ML/Data Libraries**: NumPy, Pandas, scikit-learn, scipy, torchtext, transformers
- **Visualization**: Matplotlib, Seaborn
- **Caching**: Redis, JSON file caching, In-memory caching
- **Development Tools**: Conda, Jupyter Notebook, PyCharm
- **Environment Management**: python-dotenv

### Architecture Notes

- **Educational Design**: Code is structured as teaching examples with detailed comments and step-by-step implementations
- **Progressive Complexity**: Chapters build from basic concepts to advanced implementations
- **Chinese Language Focus**: Most comments and prompt text are in Chinese
- **Self-Contained Examples**: Each file can generally run independently to demonstrate specific concepts
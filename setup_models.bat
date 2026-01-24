@echo off
echo Pulling Ollama models...

echo Pulling Qwen 2.5 14B (Main)...
ollama pull qwen2.5:14b-instruct

echo Pulling Qwen 2.5 7B (Fast)...
ollama pull qwen2.5:7b-instruct

echo Pulling DeepSeek R1 14B (Reasoning)...
ollama pull deepseek-r1:14b

echo Pulling Nomic Embed Text...
ollama pull nomic-embed-text

echo Pulling BGE-M3...
ollama pull bge-m3

echo Models updated.
pause

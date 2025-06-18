@echo off
echo  Building Docker image...
docker build -t tcf_ai_services .

echo  Starting container...
docker run -it --rm -p 8000:8000 tcf_ai_services

pause

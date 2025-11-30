
rm -rf function.zip

zip -r function.zip . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x ".env*" \
    -x ".venv*" \
    -x ".vscode*" \
    -x "venv/*" \
    -x "demo_*" \
    -x "test_*" \
    -x "*.DS_Store" \
    -x "deploy.sh" \
    -x "exec.sh" \
    -x "*.md" \
    -x "Dockerfile" \
    -x ".dockerignore" \
    -x ".funcignore"


az functionapp deployment source config-zip \
  --resource-group jfrog-budget-test \
  --name jfrog-budget-creation-function-new \
  --src function.zip

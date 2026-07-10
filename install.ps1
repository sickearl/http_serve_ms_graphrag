param(
    [string]$Path    
)
Write-Host deploy...
$cwd = $pwd
cp .\config.yaml $Path\config.yaml
cp .\settings.yaml $Path\settings.yaml
cp ___venv_Scripts_python_exe_-m_graphrag_cache.json $Path\___venv_Scripts_python_exe_-m_graphrag_cache.json
cp graphrag_startup.ps1 $Path\graphrag_startup.ps1
cp 'http serve.ps1' $Path\'http serve.ps1'
cp .\.env.default $Path\.env
cp package.json $Path\package.json

cd $Path
Write-Host creating venv
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r $cwd\requirements.txt
npm install
# .\.venv\Scripts\python.exe -m graphrag init
rm package.json
cd $cwd
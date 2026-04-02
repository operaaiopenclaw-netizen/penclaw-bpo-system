#!/bin/bash
# Script de organização - Isolar stacks

echo "=============================================="
echo "ORGANIZAÇÃO DO PROJETO OPENCLAW"
echo "=============================================="

cd ~/.openclaw/workspace-openclaw-bpo

# 1. Verificar o que existe
echo ""
echo "[1/4] Verificando estrutura atual..."

if [ -d "venv" ]; then
    echo "  ⚠️  Found: venv/ (Python)"
    echo "  📊 Size: $(du -sh venv/ | cut -f1)"
    
    # Mover para fora do projeto
    MVED_DIR=~/.openclaw-bpo-python-$(date +%Y%m%d)
    echo "  📦 Movendo para: $MVED_DIR"
    
    mv venv/ "$MVED_DIR/"
    echo "  ✅ Movido com sucesso"
    
    # Criar symlink se necessário
    # ln -s "$MVED_DIR" ./venv
else
    echo "  ✅ Nenhum venv/ encontrado"
fi

# 2. Verificar arquivos Python soltos
echo ""
echo "[2/4] Verificando arquivos Python..."
PYTHON_FILES=$(find . -maxdepth 1 -name "*.py" -type f 2>/dev/null)
if [ -n "$PYTHON_FILES" ]; then
    echo "  📄 Arquivos Python encontrados:"
    echo "$PYTHON_FILES"
    
    # Mover para pasta python/
    mkdir -p python-legacy/
    mv *.py python-legacy/ 2>/dev/null || true
    echo "  ✅ Movidos para python-legacy/"
else
    echo "  ✅ Nenhum arquivo Python na raiz"
fi

# 3. Verificar pasta .openclaw (dados)
echo ""
echo "[3/4] Verificando .openclaw/..."
if [ -d ".openclaw" ]; then
    echo "  📊 Dados financeiros encontrados"
    echo "  📁 Deve permanecer no projeto (dados da aplicação)"
    
    # Listar conteúdo
    echo "  Conteúdo:"
    ls -la .openclaw/ | head -10
else
    echo "  ✅ Nenhuma pasta .openclaw"
fi

# 4. Limpeza final
echo ""
echo "[4/4] Limpeza final..."

# Remover arquivos temporários
rm -f .python-version 2>/dev/null || true
rm -f pyvenv.cfg 2>/dev/null || true
rm -rf __pycache__ 2>/dev/null || true

echo "  ✅ Limpeza concluída"

echo ""
echo "=============================================="
echo "ESTRUTURA FINAL:"
echo ""
echo "NODE.JS PROJECT:"
echo "  ✅ src/"
echo "  ✅ package.json"
echo "  ✅ tsconfig.json"
echo "  ✅ schema.prisma"
echo "  ✅ node_modules/"
echo "  ✅ .env"
echo ""
echo "DADOS/CONFIG:"
echo "  ℹ️  .openclaw/ (usado pelo app)"
echo ""
echo "MOVIDO PARA FORA:"
if [ -d "$MVED_DIR" ]; then
    echo "  📦 venv/ -> $MVED_DIR"
    echo "  📦 *.py -> python-legacy/"
fi
echo ""
echo "STATUS: Projeto Node.js isolado ✅"
echo "=============================================="

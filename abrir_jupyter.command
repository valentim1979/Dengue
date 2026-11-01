#!/bin/bash
# Abre o Jupyter Lab na pasta do projeto. No Mac, basta clicar duas vezes neste arquivo.
# Na primeira vez cria o ambiente .venv e instala as bibliotecas (leva alguns minutos).
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "Criando o ambiente .venv (só na primeira vez)..."
  python3 -m venv .venv || { echo "Não foi possível criar o ambiente. O Python 3 está instalado?"; read -r -p "Tecle Enter para fechar."; exit 1; }
fi
source .venv/bin/activate

if ! command -v jupyter >/dev/null 2>&1; then
  echo "Instalando as bibliotecas..."
  pip install -q -r requirements.txt jupyterlab || { echo "A instalação falhou."; read -r -p "Tecle Enter para fechar."; exit 1; }
fi

echo "Abrindo o Jupyter Lab. Para encerrar, feche esta janela ou tecle Ctrl+C."
exec jupyter lab notebooks/

# 🐾 Sistema Veterinário

Este projeto é um sistema em **Flask** que reúne várias funcionalidades úteis para clínicas veterinárias e estudantes de Medicina Veterinária:

- 📋 Cadastro de usuários  
- 💊 Calculadora de doses  
- 📚 Bulário veterinário (cadastro e busca de medicamentos)  
- 👥 Componentes da Liga  
- 📄 Visualizador de artigos e documentos (com miniaturas de PDFs)  

---

## 🖥️ Apresentação visual do sistema


https://github.com/user-attachments/assets/179bec7f-164d-4e34-a97d-ab029e81735e


## 🚀 Como rodar o projeto

### 1. Clonar o repositório
bash:
git clone [link do github]
cd proj_vet

### 2. Instalar dependências
Certifique-se de ter o Python 3.8+ instalado. Depois, instale as bibliotecas necessárias:

bash:
pip install -r requirements.txt

### 3. Instalar o Poppler
O projeto usa a biblioteca pdf2image, que depende do Poppler para gerar miniaturas de PDFs.
https://github.com/oschwartz10612/poppler-windows/releases/
Configure a variável de ambiente POPPLER_PATH apontando para a pasta bin:

cmd:
set POPPLER_PATH=C:\poppler\bin

### 4. Rodar o servidor
bash
python conexao.py

### 📂 Estrutura de pastas
proj_vet/
├── pdfs/                # PDFs de teste (coloque aqui seus arquivos)
├── static/
│   ├── style/           # Arquivos CSS
│   └── thumbs/          # Miniaturas geradas automaticamente
├── templates/           # Páginas HTML (cadastro, calculadora, bulário, documentos etc.)
├── conexao.py           # Código principal Flask
├── requirements.txt     # Dependências do projeto
└── README.md            # Este arquivo

### 🛠️ Tecnologias usadas
Flask – framework web em Python

pdf2image – geração de miniaturas de PDFs

Poppler – utilitário para manipulação de PDFs

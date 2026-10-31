# Dengue – Ficha de notificação para tablet

Formulário digital baseado na **Ficha de Investigação Dengue e Febre de Chikungunya do Sinan Online** (SVS, versão 14/03/2016). Serve para coletar os dados no tablet durante epidemias, quando o volume de casos atrasa a digitação.

O formulário **não envia dados ao Sinan**. Ele gera uma tabela (CSV) para conferência e digitação no Sinan Online ou para análise.

## Como usar

1. Abra o arquivo `index.html` no navegador do tablet (Chrome, Edge ou Safari). Não precisa de internet depois de aberto.
2. Na aba **Unidade**, preencha uma vez os dados fixos (UF, município, unidade, CNES, investigador). Eles entram automaticamente em cada ficha nova.
3. Na aba **Nova ficha**, preencha e toque em **Salvar ficha**.
4. Na aba **Registros**, toque em **Baixar tabela (CSV)**. O arquivo abre no Excel, LibreOffice ou Google Planilhas.

## O que o formulário faz

- Campos numerados de 1 a 71, iguais à ficha em papel.
- Respostas gravadas com os códigos do Sinan (ex.: sexo `M/F/I`, raça `1–5, 9`, sinais clínicos `1=Sim, 2=Não`).
- Mostra só o que se aplica: dados de internação só se houve hospitalização; local de infecção só se o caso não é autóctone; blocos de sinais de alarme e dengue grave só para as classificações 11 e 12; data do óbito só se a evolução for óbito.
- Calcula a idade a partir da data de nascimento.
- Confere campos obrigatórios, datas no futuro, sintomas antes da notificação, CNS com 15 dígitos, CEP e CNES.
- Permite editar e excluir registros.
- Exporta também um **dicionário de variáveis** (nome da coluna, descrição e códigos).

## Endereço e georreferenciamento (Uniflor-PR)

O formulário já vem com a base de endereços de Uniflor (código IBGE 4128302) do **CNEFE do Censo 2022 do IBGE**: 41 combinações de bairro e rua, 1.163 pontos com coordenadas. Funciona sem internet.

- Ao digitar o bairro ou a rua, aparecem sugestões dessa base.
- Ao salvar, o formulário calcula a latitude e a longitude da residência a partir de bairro, rua e número. Abaixo do número aparece a precisão obtida.
- A tabela exportada ganha as colunas `latitude`, `longitude`, `geo_metodo` e `geo_setor` (setor censitário do IBGE, útil para agrupar casos).

Métodos da coordenada (`geo_metodo`):

| Código | Método | Quando |
|---|---|---|
| 1 | Número exato | O número existe na base do IBGE para aquela rua |
| 2 | Interpolado | Calculado entre os dois números vizinhos do mesmo lado da rua |
| 3 | Número mais próximo | O número está fora da faixa conhecida da rua |
| 4 | Centro da rua | Imóvel sem número (S/N) ou número em branco |
| 5 | Centro do bairro | A rua não está na base, mas o bairro está |

Sem rua nem bairro reconhecidos, o caso fica sem coordenada. Revise esses casos e os de método 4 e 5 antes de usar o mapa.

Os nomes das ruas vêm do IBGE sem acentos (ex.: "Rua Orquidea"). A busca ignora acentos, então "orquídea" também encontra.

### Atualizar a base

Se o IBGE publicar nova versão, baixe o CSV do município em
`https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/41_PR/`
e rode:

```
python3 scripts/gerar_base_enderecos.py dados/cnefe_2022_4128302_uniflor.csv index.html
```

O script atualiza a base dentro do `index.html` e o arquivo `dados/lista_ruas.csv`. Serve também para outro município: basta usar o CSV dele.

### Lista de ruas própria (opcional)

Se a prefeitura tiver um cadastro de logradouros mais atual, ele pode substituir as sugestões. As coordenadas continuam vindo da base do IBGE.

1. Prepare um arquivo CSV com uma linha por rua, no formato `bairro;rua`. Exemplo:
   ```
   bairro;rua
   Centro;Rua Exemplo
   Jardim Exemplo;Avenida Exemplo
   ```
2. Na aba **Unidade**, em **Lista de ruas do município**, importe o arquivo ou cole o texto e toque em **Salvar lista**.
3. Na ficha, ao digitar 3 ou 4 letras do bairro ou da rua, aparecem as sugestões. A busca ignora acentos e maiúsculas, e a rua é filtrada pelo bairro escolhido.
4. Se a rua não estiver na lista, o texto digitado é salvo assim mesmo.
5. No número, o botão **S/N** marca imóvel sem número.

A tabela exportada tem a coluna `end_na_lista`: `1` quando bairro e rua estão na lista e `2` quando foram digitados livremente. Use essa coluna para revisar os endereços antes de georreferenciar.

A lista importada fica guardada no tablet. Cada tablet precisa importar a lista uma vez. O botão **Voltar à lista do IBGE** desfaz a importação.

## Relatórios em Python

Scripts para a vigilância e para a população. Usam só `pandas` e `matplotlib`. Funcionam sem internet.

### Instalação (uma vez por computador)

Na pasta do projeto, crie um ambiente virtual e instale as bibliotecas:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt jupyterlab
```

Nas próximas vezes, basta `source .venv/bin/activate` dentro da pasta. Não é preciso instalar o conda.

### Onde colocar as tabelas

Copie os CSV exportados de cada tablet para a pasta `entrada/`. Fichas repetidas entre arquivos (por exemplo, a mesma tabela exportada duas vezes) são contadas uma vez; fica a versão gravada por último.

As pastas `entrada/` e `saida/` estão no `.gitignore` e **não vão para o GitHub**, porque contêm dados de pacientes.

### Relatório da vigilância (uso interno)

```
python3 scripts/relatorio_epidemiologico.py entrada/
```

Gera em `saida/interno/`:

- `relatorio_AAAA-MM-DD.html`: resumo, curva epidêmica por semana epidemiológica, casos por bairro (por 1.000 domicílios do CNEFE), sexo e faixa etária, sinais clínicos, oportunidade da notificação, lista de bloqueio, áreas de atenção, mapa e qualidade do georreferenciamento.
- `lista_bloqueio.csv`: casos prováveis com início dos sintomas nos últimos 14 dias, com endereço e coordenadas, para a equipe de endemias.
- `areas_atencao.csv`: círculos de 200 m centrados num caso com pelo menos 3 casos prováveis dos últimos 14 dias.
- `mapa_casos.html`: mapa interativo dos casos (precisa de internet para o mapa de fundo).
- `casos_por_se.csv` e `casos_por_bairro.csv`.

Opções: `--data-ref AAAA-MM-DD`, `--dias 14`, `--raio 200`, `--minimo 3`, `--populacao N` (para incidência por 100 mil habitantes). Veja todas com `--help`.

Definições usadas:

- **Caso provável**: toda ficha, exceto as descartadas (classificação 5).
- **Confirmado**: classificação 10, 11, 12 ou 13.
- **Semana epidemiológica**: de domingo a sábado; a semana 1 é a que contém 4 de janeiro. Conta pela data de início dos sintomas (ou de notificação, se faltar).

### Boletim para a população

```
python3 scripts/boletim_publico.py entrada/ --contato "Unidade de Saúde: (44) 0000-0000"
```

Gera em `saida/publico/`:

- `boletim_AAAA-MM-DD.png`: imagem 1080x1350 para WhatsApp, Instagram e mural.
- `boletim_AAAA-MM-DD.html`: página com a imagem e os números em texto.

O boletim **não tem nomes, endereços nem pontos no mapa**. Bairros com menos de 5 casos prováveis são somados em "Outras localidades" (ajuste com `--minimo`). Revise o texto de prevenção com a equipe antes de divulgar.

### Testar sem dados reais

```
python3 scripts/gerar_dados_teste.py 150
python3 scripts/relatorio_epidemiologico.py dados/teste/
python3 scripts/boletim_publico.py dados/teste/
```

As fichas de teste são fictícias ("Paciente Teste 001"...). Os endereços são sorteados da base do IBGE.

### Notebook para análises livres

`notebooks/exemplo_analise.ipynb` lê as fichas de `entrada/` (ou as fictícias de `dados/teste/`) e mostra exemplos: curva epidêmica, casos por bairro, tabela cruzada, filtro por sinais clínicos, tempo até a notificação, mapa e como salvar um recorte. Abra com:

```
source .venv/bin/activate
jupyter lab
```

Antes de enviar um notebook ao GitHub, limpe as saídas (*Edit → Clear Outputs of All Cells*): elas podem conter dados de pacientes.

## Tabela exportada

- Uma linha por notificação, uma coluna por variável (131 colunas).
- Separador `;` e codificação UTF-8, para abrir direto no Excel em português.
- Datas no formato `AAAA-MM-DD`.
- Os nomes de coluna seguem, quando possível, os nomes usados nas bases do Sinan. Confira com o dicionário de dados oficial antes de cruzar bases.

## Cuidados

- Os registros ficam guardados **somente no navegador do tablet** (localStorage). Limpar os dados do navegador, usar aba anônima ou trocar de navegador apaga ou esconde os registros. **Exporte a tabela ao fim de cada turno.**
- A tabela contém dados pessoais de saúde (nome, CNS, endereço e coordenadas da residência). Para mapas que vão circular, mostre os casos agrupados por setor censitário, quadra ou bairro, não pontos exatos. Guarde e transmita conforme a LGPD e as normas da secretaria de saúde.
- Os campos marcados como obrigatórios foram definidos a partir da ficha em papel. Ajuste conforme a orientação da vigilância local.

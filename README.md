# Dengue – Ficha de notificação para tablet (15ª Regional de Saúde – PR)

Formulário digital baseado na **Ficha de Investigação Dengue e Febre de Chikungunya do Sinan Online** (SVS, versão 14/03/2016), para coletar dados no tablet durante epidemias. Atende os 30 municípios da 15ª Regional de Saúde (Maringá).

O formulário **não envia dados ao Sinan**. As fichas vão para uma planilha Google da vigilância, para conferência, digitação no Sinan Online e análise.

**Link do formulário:** `https://valentim1979.github.io/Dengue/` (funciona depois de ativar o GitHub Pages; veja abaixo).

## Para as unidades de saúde

1. Abra o link no navegador do tablet (Chrome, Edge ou Safari), com internet.
2. Opcional: no menu do navegador, toque em **Adicionar à tela inicial**. O formulário vira um ícone, como um aplicativo.
3. Na aba **Unidade**, preencha uma vez:
   - município de notificação (escolha na lista), unidade, CNES e investigador;
   - município de residência mais comum (o da própria unidade);
   - **endereço do envio** e **chave de envio**, fornecidos pela vigilância.
   Toque em **Salvar** e em **Salvar e testar**. Depois toque em **Baixar base do município da unidade**.
4. Na aba **Nova ficha**, preencha e toque em **Salvar ficha**.

Depois da primeira abertura com internet, o formulário funciona **sem internet**. Fichas salvas sem conexão ficam na fila e são enviadas sozinhas quando a internet volta (ou pelo botão **Enviar pendentes agora**). A aba **Registros** mostra o que já foi enviado.

Mesmo com o envio automático, exporte de vez em quando a tabela (**Registros → Baixar tabela (CSV)**) como cópia de segurança. Limpar os dados do navegador apaga as fichas do tablet.

## O que o formulário faz

- Campos 1 a 71 da ficha, gravados com os códigos do Sinan (ex.: sexo `M/F/I`, raça `1–5, 9`, sinais `1=Sim, 2=Não`).
- Mostra só o que se aplica: internação, local de infecção, sinais de alarme e dengue grave, data do óbito.
- Calcula a idade pela data de nascimento e confere campos obrigatórios, datas e formatos (CNS, CEP, CNES).
- Município de notificação e de residência com lista dos 30 municípios da 15ª RS e código IBGE automático.
- Bairro e rua com sugestões da base do IBGE do município de residência; número com botão **S/N**.
- Calcula latitude e longitude da residência ao salvar.

## Endereço e georreferenciamento

As bases de endereços ficam em `bases/<código IBGE>.json`, geradas do **CNEFE do Censo 2022 (IBGE)**. O tablet baixa só a base do município de residência informado e a guarda para uso sem internet. A de Maringá tem 5,5 MB; as demais, menos de 2 MB.

Colunas de georreferenciamento na tabela: `latitude`, `longitude`, `geo_metodo`, `geo_setor` (setor censitário) e `end_na_lista`.

| `geo_metodo` | Método | Quando |
|---|---|---|
| 1 | Número exato | O número existe na base do IBGE para aquela rua |
| 2 | Interpolado | Entre os dois números vizinhos do mesmo lado da rua |
| 3 | Número mais próximo | O número está fora da faixa conhecida da rua |
| 4 | Centro da rua | Imóvel sem número (S/N) ou número em branco |
| 5 | Centro do bairro | A rua não está na base, mas o bairro está |

Residência fora da 15ª RS, rua e bairro não encontrados, ou base não baixada: o caso fica sem coordenada. Os nomes das ruas vêm do IBGE sem acentos; a busca ignora acentos.

Para incluir outro município ou atualizar as bases, baixe o CSV do município em
`https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/CSV/Municipio/41_PR/`, descompacte e rode:

```
python3 scripts/gerar_base_enderecos.py PASTA_COM_OS_CSV
```

## Para a vigilância: publicar o link (GitHub Pages)

No repositório: **Settings → Pages → Source: Deploy from a branch → Branch: main, pasta / (root) → Save**. Em alguns minutos o link `https://valentim1979.github.io/Dengue/` passa a funcionar.

O repositório é público, mas contém só o código e a base de endereços do IBGE (dados públicos). **Nenhuma ficha de paciente vai para o GitHub.**

## Para a vigilância: planilha que recebe as fichas

As fichas chegam numa planilha Google, numa pasta do Drive da vigilância, por meio de um script (Google Apps Script). Faça uma vez:

1. No Google Drive, crie (ou escolha) a pasta das respostas e, dentro dela, uma **planilha Google** nova (ex.: "Fichas dengue 15ª RS").
2. Na planilha: **Extensões → Apps Script**. Apague o conteúdo e cole o arquivo [`apps_script/Code.gs`](apps_script/Code.gs). Salve.
3. No Apps Script: **Configurações do projeto** (engrenagem) → **Propriedades do script** → **Adicionar propriedade**: nome `CHAVE`, valor = uma senha longa (20 ou mais letras e números). Salve.
4. **Implantar → Nova implantação** → tipo **App da Web**. *Executar como:* **Eu**. *Quem pode acessar:* **Qualquer pessoa**. Clique em **Implantar** e autorize.
5. Copie a **URL do app da Web** (termina em `/exec`). Envie a URL e a `CHAVE` às unidades por um canal seguro (não publique a chave).

As fichas aparecem na aba **fichas** da planilha, uma linha por ficha, com a coluna `recebido_em`. Uma ficha editada no tablet e reenviada substitui a linha anterior (mesmo `id_registro`). Uma ficha excluída no tablet **não** é apagada da planilha.

Se o script for alterado, publique de novo em **Implantar → Gerenciar implantações → editar → Nova versão**, para manter a mesma URL.

**LGPD:** a planilha contém dados pessoais de saúde. Restrinja o compartilhamento da pasta à equipe da vigilância e confirme com o responsável pela proteção de dados se o uso do Google Drive é permitido.

## Relatórios em Python

Usam só `pandas` e `matplotlib` e funcionam sem internet.

### Instalação (uma vez por computador)

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt jupyterlab
```

No Mac, há o atalho `abrir_jupyter.command` (clique duplo), que faz isso e abre o Jupyter Lab.

### De onde vêm as fichas

Baixe a planilha: **Arquivo → Fazer download → Valores separados por vírgula (.csv)**, com a aba **fichas** aberta, e salve em `entrada/`. Também servem os CSV exportados direto dos tablets. Fichas repetidas são contadas uma vez (fica a versão gravada por último).

As pastas `entrada/` e `saida/` estão no `.gitignore` e **não vão para o GitHub**.

### Relatório da vigilância (uso interno)

```
python3 scripts/relatorio_epidemiologico.py entrada/ --municipio 4115200
```

Sem `--municipio`, usa o município de residência mais frequente nas fichas e avisa quais outros há. Gera em `saida/interno/` (com o código do município no nome):

- `relatorio_CODIGO_AAAA-MM-DD.html`: resumo, curva epidêmica, casos por bairro (por 1.000 domicílios do CNEFE), sexo e faixa etária, sinais clínicos, oportunidade da notificação, lista de bloqueio, áreas de atenção, mapa e qualidade do georreferenciamento.
- `lista_bloqueio_CODIGO.csv`: casos prováveis com início dos sintomas nos últimos 14 dias, com endereço, para a equipe de endemias.
- `areas_atencao_CODIGO.csv`: círculos de 200 m centrados num caso, com pelo menos 3 casos prováveis dos últimos 14 dias.
- `mapa_casos_CODIGO.html`: mapa interativo (precisa de internet para o mapa de fundo).
- `casos_por_se_CODIGO.csv` e `casos_por_bairro_CODIGO.csv`.

Opções: `--data-ref AAAA-MM-DD`, `--dias 14`, `--raio 200`, `--minimo 3`, `--populacao N` (incidência por 100 mil hab.). Veja todas com `--help`.

Definições:

- **Caso provável**: toda ficha, exceto as descartadas (classificação 5).
- **Confirmado**: classificação 10, 11, 12 ou 13.
- **Semana epidemiológica**: de domingo a sábado; a semana 1 contém 4 de janeiro. Conta pela data de início dos sintomas (ou de notificação, se faltar).

### Boletim para a população

```
python3 scripts/boletim_publico.py entrada/ --municipio 4128302 --contato "Unidade de Saúde: (44) 0000-0000"
```

Gera em `saida/publico/` uma imagem 1080x1350 (WhatsApp, Instagram, mural) e uma página HTML. **Sem nomes, endereços ou pontos no mapa.** Bairros com menos de 5 casos prováveis são somados em "Outras localidades" (ajuste com `--minimo`). Revise o texto de prevenção com a equipe antes de divulgar.

### Notebook para análises livres

`notebooks/exemplo_analise.ipynb` mostra curva epidêmica, casos por bairro, tabela cruzada, filtro por sinais clínicos, tempo até a notificação, mapa e como salvar um recorte. Abra com `jupyter lab`. Antes de enviar um notebook ao GitHub, limpe as saídas (*Edit → Clear Outputs of All Cells*).

### Testar sem dados reais

```
python3 scripts/gerar_dados_teste.py 150
python3 scripts/gerar_dados_teste.py 300 dados/teste/maringa.csv --municipio 4115200
python3 scripts/relatorio_epidemiologico.py dados/teste/
python3 scripts/boletim_publico.py dados/teste/
```

As fichas de teste são fictícias ("Paciente Teste 001"...). Os endereços são sorteados da base do IBGE.

## Tabela exportada

- Uma linha por notificação, uma coluna por variável (131 colunas). No tablet: separador `;`, UTF-8. Na planilha Google: mais a coluna `recebido_em`.
- Datas no formato `AAAA-MM-DD`.
- Os nomes de coluna seguem, quando possível, os das bases do Sinan. Confira com o dicionário de dados oficial antes de cruzar bases. O dicionário de variáveis sai em **Registros → Baixar dicionário de variáveis**.

## Cuidados

- As fichas contêm dados pessoais de saúde (nome, CNS, endereço e coordenadas da residência). Para mapas que vão circular, mostre os casos agrupados por setor censitário, quadra ou bairro, não pontos exatos.
- A chave de envio dá acesso de gravação à planilha. Troque-a (propriedade `CHAVE` no Apps Script) se ela vazar, e informe a nova às unidades.
- Os campos obrigatórios foram definidos a partir da ficha em papel. Ajuste conforme a orientação da vigilância.

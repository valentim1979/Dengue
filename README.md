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

## Lista de ruas (endereço padronizado)

Para facilitar o georreferenciamento, bairro e logradouro podem ser escolhidos de uma lista de ruas do município.

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

A lista fica guardada no tablet. Cada tablet precisa importar a lista uma vez.

## Tabela exportada

- Uma linha por notificação, uma coluna por variável (127 colunas).
- Separador `;` e codificação UTF-8, para abrir direto no Excel em português.
- Datas no formato `AAAA-MM-DD`.
- Os nomes de coluna seguem, quando possível, os nomes usados nas bases do Sinan. Confira com o dicionário de dados oficial antes de cruzar bases.

## Cuidados

- Os registros ficam guardados **somente no navegador do tablet** (localStorage). Limpar os dados do navegador, usar aba anônima ou trocar de navegador apaga ou esconde os registros. **Exporte a tabela ao fim de cada turno.**
- A tabela contém dados pessoais de saúde (nome, CNS, endereço). Guarde e transmita conforme a LGPD e as normas da secretaria de saúde.
- Os campos marcados como obrigatórios foram definidos a partir da ficha em papel. Ajuste conforme a orientação da vigilância local.

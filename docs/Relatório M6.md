Estrutura do Relatório M6 — Plano de Negócios
Datas: Entrega 2026-06-01 | Apresentação 2026-06-02

Formatação: Arial 10 | Espaçamento 1,5 | Justificado | Margens esq./sup. 2,5 cm, dir./inf. 2 cm

Elementos Fixos (não contam para o limite de páginas)
Capa (empresa, G18, nº mecanográfico, nomes, "M6", data)
Índice
Introdução
Conclusão
Bibliografia
Anexos (incl. ferramenta informática)
Corpo do Relatório
a) Ideia Inovadora de Investimento

Contributo inovador fundamentado (rever CANVAS do M1)
Contextualização do negócio
Produtos/serviços a desenvolver
Mercado alvo (definição e caracterização)
Recursos necessários
Cronograma do projeto
Resultados esperados
(Metodologia sugerida: Matriz de Ansoff)
b) Objetivos e Posicionamento Estratégico

c) Estratégia de Marketing

Marketing-mix (Produto, Preço, Praça, Promoção — Kotler)
d) Gestão da Produção e Tecnologia

e) Qualidade e Sustentabilidade

Objetivos de Desenvolvimento Sustentável (ODS) aplicáveis
f) Gestão e Controlo do Negócio

Funções de gestão, estrutura organizacional, SCI
g) Investimentos a Realizar ← restrição crítica

O valor em ativos não correntes deve ser obrigatoriamente entre 15% e 30% do ATL do último ano histórico.

Vários ANC (com propostas/orçamentos se possível)
Investimento em Fundo de Maneio
Reservas para imprevistos
Cronologia de execução
h) Modelo de Financiamento ← requisito mínimo obrigatório

≥2 fontes distintas de capital alheio (ex: CGD/BPI + PT2030) — justificadas
Capital próprio se o equilíbrio financeiro o exigir
Mapas de serviço da dívida por fonte
i) Projeções Económicas e Financeiras

DR, DFC e Balanços previsionais (com projeto vs. M3 sem projeto)
DR comparativas com pesos relativos no VBP
Balanços comparativos com pesos relativos no ATL
Balanço funcional + indicadores financeiros
Avaliação de riscos (externos e internos)
Cash-flows + VAL, TIR, Payback, Índice de Rendibilidade
Análise de sensibilidade às variáveis críticas (tornado)
Análise de cenários
j) Análise da Viabilidade Económica e Financeira

k) Análise de Sensibilidade

l) Plano de Contingência

Síntese Final (obrigatória)
CANVAS atualizado (9 dimensões + cronograma de implementação)
Conclusão da viabilidade do projeto + impacto na estrutura económico-financeira
Plano de contingência
OE4 (integrado no M6, entrega separada até 2026-05-25, máx. 12 págs)
Equilíbrio financeiro pré-projeto (autonomia financeira, solvabilidade, endividamento)
Mapa de investimento
Plano de financiamento (≥2 fontes capital alheio + CP se necessário)
Mapas de serviço da dívida
Demonstração de ≥30% autonomia financeira pós-projeto ← condição sine qua non
Economias fiscais + enquadramento PT2030
No contexto da vossa ferramenta
O modelo já produz quase tudo o que o ponto i) exige:

Requisito M6	Onde no GrestelPy
DR/Balanço/DFC com e sem Hub	Cenário Base ↔ toggle Hub
VAL, TIR, Payback, IR	/api/hub/viability
Análise de sensibilidade	/api/hub/tornado
Mapa de serviço da dívida	/api/hub/debt-service
Mapa de investimento (CAPEX + NFM)	/api/hub/investment-map
Equilíbrio financeiro pré/pós	Separador KPIs (autonomia financeira, solvabilidade)
Análise de cenários	4 cenários Base/Upside/Downside/Stress
A parte que falta no relatório (e que a ferramenta não gera automaticamente) é a narrativa qualitativa: secções a–f, o CANVAS atualizado, e o plano de contingência.

Como enquadrar o a) para o Hub Logístico
O problema do template vs. a vossa realidade:

O template fala em "produtos/serviços a desenvolver" pressupondo uma nova linha de negócio. No vosso caso, o Hub é a ideia inovadora — não é um produto, é uma mudança da forma como a empresa opera. Tens de adaptar cada sub-alínea para que faça sentido neste contexto.

Sub-alínea por sub-alínea
1. Contributo Inovador Fundamentado
Não é inovação de produto — é inovação de processo e modelo operacional. Justifica assim:

A Grestel exporta >90% do VN mas opera com lógica de armazenagem fragmentada e expedições diretas à saída da fábrica
O Hub centraliza a operação logística (consolidação de carga, picking automatizado, gestão de stock JIT) e incorpora tecnologias Indústria 4.0 (VLMs, AMRs, WMS)
O contributo inovador é a eliminação do gargalo logístico como alavanca de crescimento sustentado e redução de custos — não a criação de um novo produto
2. Contextualização do Negócio
Usa os dados do vosso próprio modelo:

CCC de 297 dias (dados do balanço 2024), 13 M€ imobilizados em inventário
Custo de FSE logísticos externos que o hub vai substituir
Picos sazonais (Natal, Mother's Day EUA) sem capacidade de resposta rápida atual
3. "Produtos/Serviços a Desenvolver"
Aqui respondes com os serviços logísticos do Hub, não produtos cerâmicos:

Armazenagem automatizada (VLMs/AMRs)
Picking e packing por canal (B2B / D2C e-commerce)
Cross-docking para encomendas urgentes
Consolidação de contentores marítimos
Logística inversa e serviços de valor acrescentado (kitting, embalagem privada)
Fase 2 (ano 3+): serviços a terceiros (cluster cerâmico de Aveiro/Coimbra)
4. Mercado-Alvo
Dois níveis:

Imediato (cativo): Grestel + Costa Nova + Mr. Bowl Ceramics — o hub serve o grupo, não um mercado externo
Futuro (ano 3+): produtores cerâmicos da região em regime de outsourcing logístico
5. Recursos Necessários
Já estão no modelo — cita diretamente o mapa de investimento (CAPEX 3,8 M€):

Reabilitação da unidade G1 (lote 29 — Grestel já detém o terreno)
4 VLMs + 3 AMRs fase 1 + Cobots
WMS integrado com ERP
Equipa logística (gestor + operadores + IT)
6. Cronograma
Usa o do modelo:

2025 H1: projeto de engenharia + candidatura PT2030
2025 H2: construção civil + instalação
2026 H1: comissionamento + arranque faseado
2026 H2 em diante: operação plena
7. Resultados Esperados
Tira diretamente da API (/api/hub/viability):

Poupança operacional: 380 k€/ano (pessoal + FSE)
Redução de quebras: 50 k€/ano
Libertação de inventário: 2 M€ (2026, one-time)
VAL positivo, TIR > WACC, Payback descontado ~4,7 anos
Matriz de Ansoff
Este é o ponto onde formalizas o posicionamento estratégico. Para o Hub:

Mercados Actuais	Mercados Novos
Produtos Actuais	Penetração de Mercado ← Hub melhora serviço aos clientes existentes	Desenvolvimento de Mercado
Produtos Novos	Desenvolvimento de Produto	Diversificação
O quadrante principal é Penetração de Mercado: os mesmos produtos cerâmicos, aos mesmos clientes, mas com nível de serviço superior (lead time, OTIF, rastreabilidade) que reforça a posição competitiva e justifica o premium de preço.

A Fase 2 (serviços a terceiros) é Diversificação — novo serviço, novo mercado — mas é secundária e pode ser mencionada como opção de upside.

Este posicionamento na Ansoff é academicamente correto e tem a vantagem de não exigir projeções de receita nova para o core do projeto — o valor vem da eficiência, não do crescimento de VN.

O que não precisas de inventar
A secção a) não requer dados financeiros — é narrativa qualitativa. Os dados todos (CAPEX, poupanças, VAL, cronograma) ficam para as secções g), h) e i). Na alínea a) mostras apenas que a ideia é coerente, fundamentada e inovadora. Com o que está no hub_logistico_info.md tens substância mais do que suficiente para 2–3 páginas bem escritas.

O princípio fundamental
M6 não é um apêndice de M3 — é um documento autónomo que usa M3 como ponto de partida. O regulamento diz "rever, se necessário, o definido em M1". Podes (e deves) actualizar o que está errado, desde que o faças explicitamente. Contradições não assumidas é que penalizam.

Fase 0 — Auditoria (1-2 horas, fazer antes de escrever qualquer linha)
Cria uma tabela de três colunas num documento auxiliar:

Item	O que está em M1/M3	O que está no modelo agora	Decisão
VN 2024	?	37,88 M€ (R&C auditado)	manter
RL 2024	?	1,39 M€	manter
SMART obj. 1 (VN)	45,6 M€ em 2027	modelo prevê ~41 M€ em 2027	rever
SMART obj. 2 (EBITDA%)	≥19,5% em 2027	modelo prevê ~14%	rever
SMART obj. 3 (AF)	≥35%	modelo: cumpre	manter
SMART obj. 4 (CCC)	260 dias em 2027	Hub reduz → verificar	actualizar com hub
Ideia inovadora (CANVAS)	? de M1	Hub Logístico	actualizar
CAPEX investimento	?	6,0 M€ (fases 1+2 integradas)	✅ 15,1 % do ATL — cumpre mínimo 15 %
A "decisão" é sempre uma de três opções:

Manter — coincide com o modelo, sem conflito
Rever — o modelo corrigiu, M6 adopta o novo valor com nota explicativa
Actualizar com hub — M3 era sem projecto, M6 é com projecto (diferença legítima e esperada)
Fase 1 — O que extrair do modelo (números que já tens)
Corre a API e exporta para o relatório:

Secção M6	Fonte no GrestelPy
SMART revistos (valores-alvo)	/api/scenarios/all → cenário Base com Hub
DR 2024-2029 sem projecto	cenário Base, hub_on=false
DR 2024-2029 com projecto	cenário Base, hub_on=true
Balanço comparativo	idem
DFC comparativa	idem
KPIs / rácios	separador KPIs
VAL, TIR, Payback, IR	/api/hub/viability
Análise de sensibilidade	/api/hub/tornado
Mapa de serviço da dívida	/api/hub/debt-service
Mapa de investimento CAPEX	/api/hub/investment-map
Autonomia financeira pós-projecto	KPIs com hub_on=true
Fase 2 — SMART revistos para M6
Os do SMART.md foram feitos para M3 (sem Hub). Para M6, os objectivos têm de reflectir o plano com Hub. Regra: lê o valor do modelo e constrói o SMART em torno disso.

Como reescrever cada um:

1. Volume de Negócios
O modelo com Hub prevê crescimento via VN incremental B2C. Não inventes 45,6 M€ se o modelo não chega lá. Usa o que o modelo produz, ex:

"Atingir VN de [valor do modelo] M€ em 2027, impulsionado pela melhoria do nível de serviço decorrente do Hub Logístico e pela consolidação do canal e-commerce Costa Nova."

2. Margem EBITDA
O Hub tem poupança de 380 k€/ano mas também gera depreciações. Lê o EBITDA% do modelo com hub_on=true em 2027. Esse é o alvo realista.

3. Autonomia Financeira
Este era o mais sólido. Confirma que o modelo com Hub mantém AF ≥ 30% (requisito OE4). Se cumprir, mantém o objectivo em ≥ 35% (buffer).

4. Ciclo de Conversão de Caixa (CCC)
O Hub liberta 2 M€ de inventário em 2026. O CCC de 297 dias desce. Calcula o CCC implícito no balanço com hub_on=true em 2027 e usa esse número.

5. ESG / Sustentabilidade
O modelo tem esg_2024 com gas_por_peca_kwh: 0.7394. O objectivo de -10% → 0.665 kWh/peça em 2027 mantém-se independentemente do Hub. Manter.

Fase 3 — Estrutura de escrita (sequência recomendada)
Escreve nesta ordem, não na ordem das alíneas:


1.º  g) Investimentos          ← âncora de tudo; define o projecto
2.º  h) Financiamento          ← deriva de g); OE4
3.º  i) Projeções financeiras   ← corre modelo, cola outputs
4.º  j) Viabilidade            ← VAL/TIR/Payback da API
5.º  k) Sensibilidade          ← tornado da API
6.º  b) Objectivos SMART       ← agora sabes o que é atingível
7.º  a) Ideia inovadora        ← narrativa que enquadra g)+b)
8.º  c) Marketing              ← Kotler aplicado ao Hub
9.º  d) Produção/Tecnologia     ← VLMs, AMRs, WMS
10.º e) Sustentabilidade        ← ODS 9, 12, 13
11.º f) Gestão/Controlo         ← organograma, SCI
12.º Síntese CANVAS            ← fecha com o Business Model Canvas
13.º l) Contingência           ← riscos e plano B
14.º Introdução + Conclusão    ← escreve por último
Porquê esta ordem? As secções qualitativas (a, c, d, e, f) têm de ser coerentes com os números. Se escreveres a narrativa antes de saber os números, vais reescrever tudo.

Fase 4 — Gestão das divergências com M3
Não tens de fingir que M3 estava perfeito. O M6 pode (e às vezes deve) dizer:

"As projeções de continuidade apresentadas em M3 foram revistas para M6 com base em [razão]. O cenário de referência sem projecto mantém os pressupostos de M3 na sua essência, com as seguintes actualizações: [lista]."

As divergências aceitáveis são:

Números actualizados com R&C 2024 completo (M3 pode ter sido feito com dados preliminares)
SMART ajustados ao que o modelo efectivamente projecta
Incorporação do Hub (M3 era sem projecto — é uma diferença estrutural e esperada)
A divergência que não podes ter é contradição directa sem explicação (ex: M3 dizia VN 2027 = X, M6 diz VN 2027 = Y sem nota alguma).

Checklist de consistência obrigatória M3 → M6
Antes de entregar, confirma:

 Ano base histórico é o mesmo em M1, M3 e M6 (2024)
 VN 2024 e RL 2024 coincidem (37,88 M€ / 1,39 M€)
 As projeções "sem projecto" de M6 são iguais ou próximas de M3 (ou há nota de revisão)
 CAPEX Hub está entre 15% e 30% do ATL 2024 → ATL 2024 ≈ 39,7 M€ → intervalo: 5,9 M€ a 11,9 M€ → ✅ 6,0 M€ = 15,1 % (fases 1+2 integradas — cumpre)
 AF pós-projecto ≥ 30% (confirmar na API com hub_on=true)
 SMART têm valores que o modelo efectivamente produz
 CANVAS actualizado tem 9 blocos preenchidos com dados concretos
✅ Ponto crítico resolvido: O CAPEX foi revisto para 6,0 M€ (integração fases 1+2), representando 15,1% do ATL de 39,7 M€ — cumpre o mínimo de 15% exigido. A integração das fases é financeiramente coerente: economias de escala nas obras civis, menor risco de interrupção operacional e aproveitamento único da janela PT2030.

Para o caso de um projeto focado em **eficiência logística** — especificamente a criação de um **Hub Logístico Integrado e Inteligente (Costa Nova Logistics Hub 4.0)** — a estrutura do M6 e da OE4 deve ser preenchida com os detalhes técnicos e financeiros específicos desta solução inovadora.

Abaixo, detalho como deve adaptar as estruturas para este tema, integrando as correções de valores (EUR/USD, Euribor e Inflação) já discutidas.

### 1. Estrutura do Relatório M6 (Focada em Eficiência Logística)

O relatório deve demonstrar como a automação logística resolve os gargalos da Grestel.

*   **Apresentação da Ideia Inovadora:**
    *   **Contributo Inovador:** Substituir o picking manual e a armazenagem fragmentada por um sistema de torres automáticas (**VLMs**) e robots autónomos (**AMRs**).
    *   **Contextualização:** Focar na dependência do transporte marítimo e nos picos sazonais (Natal/Black Friday) que geram gargalos de expedição.
    *   **Recursos:** Implementação de um **WMS** (*Warehouse Management System*) integrado com o ERP e tecnologias de **Visão IA** para embalamento.
*   **Estratégia e Operações:**
    *   **Objetivos SMART (Revistos):** Reduzir o período médio de cobertura de stock em **20 dias**; atingir um **OTIF ≥ 98%**; reduzir a pegada de CO2 logística em **25%**.
    *   **Marketing-Mix:** O "Produto" passa a incluir um serviço logístico premium com rastreabilidade digital total para clientes como a Le Creuset.
    *   **Tecnologia:** Uso de robots colaborativos (**Cobots**) e linha *Box-on-Demand* para reduzir desperdício de cartão.
*   **Investimentos (Respeitar limite 15%-30% do ATL):**
    *   **Otimização do CAPEX:** Em vez de construção nova, utilizar a **reabilitação da Unidade G1** (Lote 29), já detida pela empresa, para reduzir o investimento inicial.
    *   **Faseamento:** Propor uma Fase 1 com CAPEX de **3,8 M€** (focada no core VLM e WMS) e diferir componentes como o *Digital Twin* para a Fase 2.
*   **Análise Financeira e de Viabilidade:**
    *   **Drivers de Benefício:** Libertação de **2 M€ de capital imobilizado em inventário** no primeiro ano.
    *   **Comparação de Cenários:** Demonstrar o impacto no EBITDA comparando o cenário "Sem Hub" (M3 corrigido) vs. "Com Hub".
    *   **Indicadores:** Almejar um **Payback descontado de ~4,7 anos** (melhorado face aos 8 anos originais pela via da otimização do CAPEX).

---

### 2. Estrutura da OE4 (Plano de Financiamento do Hub)

A OE4 deve garantir que este investimento de grande escala não compromete os *covenants* bancários (Autonomia Financeira ≥ 30%).

*   **Situação Pré-Projeto:** Referir que a Grestel tem uma Autonomia Financeira robusta (~30.3% em 2024), mas com tesouraria líquida sob pressão devido ao elevado nível de inventários.
*   **Mapa de Investimento:**
    *   **Ativos fixos:** Equipamentos AMRs/VLMs, preparação do terreno e reabilitação de edifício.
    *   **Fundo de Maneio:** Modelar a **redução das necessidades de fundo de maneio** decorrente da maior eficiência na rotação de stocks.
*   **Plano de Financiamento (Mínimo 2 fontes alheias):**
    *   **Fonte 1 (Prioritária):** Candidatura ao **Portugal 2030 / Compete 2030** (Eixo Inovação/Digitalização) com taxa de subsídio majorada para **45%** devido ao pendor tecnológico e sustentável.
    *   **Fonte 2:** Empréstimo bancário MLP (médio/longo prazo) ou **Leasing Financeiro** especificamente para os robôs e torres automáticas.
    *   **Capitais Próprios:** Utilizar o autofinanciamento (retenção de resultados) para cobrir a parcela restante, assegurando o equilíbrio pós-projeto.
*   **Mapas de Serviço da Dívida:** Criar o plano de amortização para o novo empréstimo bancário, integrando a taxa de juro baseada na **Euribor de 2,90%** (correção do M3) [Conversa Anterior, 10].

### Integração das Correções M3 no M6 e OE4

Ao preparar estes relatórios, assegure-se de que os pressupostos base seguem os valores retificados:
1.  **Exposição Cambial:** No cenário de continuidade e de projeto, a sensibilidade ao USD deve incidir sobre **21% do Volume de Negócios total**, resultando num impacto de **-705 k€** no EBITDA para um choque de 10% [Conversa Anterior].
2.  **Inflação 2025:** Todos os custos incrementais de pessoal para operar o Hub devem crescer a **3,12% nominal** (0,8% real + 2,3% inflação) [Conversa Anterior].
3.  **Taxa de Juro:** O financiamento do Hub na OE4 deve ser calculado com **Euribor 3M de 2,90% + Spread**, garantindo coerência com o cenário macroeconómico do M3 [Conversa Anterior].

Esta abordagem de **eficiência logística** é estratégica para a Grestel, pois ataca diretamente o problema do **Ciclo de Conversão de Caixa elevado (297 dias)**, libertando liquidez para novos investimentos.
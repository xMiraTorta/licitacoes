# Pesquisa de frete para café torrado saindo de Uberaba-MG

Data da pesquisa: 18/10/2026. Todos os números abaixo têm fonte e data. As cotações simuladas foram feitas por nós nos sites públicos da Jadlog e dos Correios em 18/10/2026, entre 02:50 e 03:07 (horário de Brasília). Os dados brutos estão em `pesquisa_frete.json`.

## Resumo em 6 linhas

1. **Fórmula proposta, por entrega (fracionado):** `frete = R$ 180 + kg × (R$ 2,10 + R$ 0,23 × km/100) + 0,8% do valor da nota`.
2. **Alternativa por entrega (caminhão dedicado de 2 eixos, piso ANTT):** `frete = R$ 451,84 + R$ 4,0738 × km`, mais pedágio. Use o menor dos dois.
3. **Várias entregas:** calcule cada entrega com o peso dela e some. Dividir 1.000 kg em 12 entregas custa de 39% a 56% a mais que uma entrega só.
4. **Quando compensa a lotação (caminhão só seu):** acima de ~240 kg a 100 km, ~450 kg a 300 km, ~680 kg a 600 km, ~880 kg a 1.000 km e ~1.160 kg a 2.000 km.
5. **Para amostras e pacotes até 30 kg:** Correios PAC (R$ 86 a R$ 346 por caixa de 10 kg, conforme o destino).
6. **Atenção:** a fórmula foi calibrada com preço de balcão da Jadlog (sem contrato). O erro médio é de 17% e, em alguns destinos, passa de 30%. Para cada licitação boa, peça cotação real.

## 1. Piso mínimo da ANTT (Lei 13.703/2018)

**Tabela vigente:** Resolução ANTT 6.084/2026, reajustada pela Portaria SUROC nº 22, de 28/09/2026. Foi publicada no DOU (edição extra) em 29/09/2026 e vale desde 30/09/2026, com diesel de referência a R$ 7,33/L (fontes: [Transp.net](https://www.transp.net/calculadora-frete-antt), [Gefrota](https://www.gefrota.com.br/piso-minimo-de-frete/tabela-antt), [contadores.cnt.br](https://www.contadores.cnt.br/legislacoes/portaria-suroc-no-22-de-28-09-2026.html)). A reportagem da [Tecnologística (20/07/2026)](https://www.tecnologistica.com.br/noticias/transporte-rodoviario/21651/antt-atualiza-tabela-do-piso-minimo-de-frete-confira-os-novos-valores/) traz a versão anterior (2 eixos: R$ 3,9826/km). Houve também um reajuste em março, pela Portaria SUROC 3/2026 ([ANTT](https://www.gov.br/antt/pt-br/assuntos/ultimas-noticias/antt-atualiza-tabela-dos-pisos-minimos-de-frete-em-decorrencia-da-variacao-no-preco-do-diesel-s10)).

**Calculadora oficial:** [calculadorafrete.antt.gov.br](https://calculadorafrete.antt.gov.br). O texto da portaria está no DOU. O site contadores.cnt.br recusou nosso acesso (erro 403), por isso os coeficientes vêm de duas páginas de terceiros que concordam entre si.

**Tabela A, carga geral, lotação (veículo com carroceria):** piso = km × CCD + CC

| Eixos | Tipo comum | CCD (R$/km) | CC, carga e descarga (R$) |
|---|---|---|---|
| 2 | VUC, 3/4, toco | 4,0738 | 451,84 |
| 3 | truck | 5,2177 | 541,86 |
| 4 | bitruck | 5,9180 | 588,86 |
| 5 | carreta | 6,8284 | 657,56 |
| 6 | carreta trucada | 7,5347 | 671,93 |
| 7 | bitrem | 8,2727 | 831,66 |
| 9 | rodotrem | 9,4114 | 903,32 |

O que isso quer dizer na prática:
- **Veículos pequenos:** a tabela não tem linha própria para VUC ou 3/4. Ela é organizada por número de eixos, e VUC, 3/4 e toco têm 2 eixos, então entram na linha de 2 eixos. Essa é a nossa leitura da tabela, não um texto da ANTT.
- **O piso fica abaixo do preço de mercado.** Pela Res. 5.867/2020, ele não inclui lucro, pedágio, tributos nem despesas administrativas, e o pedágio deve ser somado ([LegisWeb](https://www.legisweb.com.br/legislacao/?id=388856)). A volta vazia só entra no caso de contêiner e de frota dedicada.
- **Carga fracionada não tem piso próprio.** A tabela foi feita para lotação. Em 2026, a Portaria SUROC 16/2026 passou a tratar como lotação a operação com um único contratante, mesmo com vários destinos, e há divergência jurídica sobre isso ([VLF Advogados](https://vlf.adv.br/noticia_aberta.php?id=3565); [SETCESP](https://setcesp.org.br/noticias/fiscalizacao-automatica-da-antt-expoe-falhas-no-piso-minimo-do-frete-e-pressiona-o-frete-fracionado/)).

## 2. Carga fracionada: como cobram e quanto custa

### Componentes do preço (referências de mercado)

| Componente | Como é cobrado | Valor de referência | Fonte e data |
|---|---|---|---|
| Frete-peso | R$ por faixa de kg e região; vale o maior entre o peso real e o peso cubado | depende da tabela da transportadora | [Favorita](https://blog.favorita.com.br/transporte-fracionado/) |
| Frete-valor (ad valorem) | % sobre a nota | 0,30% a 1,2% conforme a distância | [SETCESP/IPTC, 01/10/2023](https://setcesp.org.br/noticias/veja-como-fica-a-nova-composicao-tarifaria-na-formacao-do-frete/) |
| GRIS (risco de roubo) | % sobre a nota | 0,30%, mínimo de cerca de R$ 3 por CT-e | [Simfrete, 05/08/2026](https://www.simfrete.com.br/blog/gris-ad-valorem-pedagio-e-taxas-adicionais-o-que-realmente-compoe-o-custo-do-frete) |
| TSO (seguro obrigatório) | % sobre a carga | 0,15% a 0,30%, mínimo de R$ 4,90 | SETCESP 2023 |
| Despacho | valor fixo por conhecimento (CT-e) | varia | Simfrete 2026 |
| Pedágio | rateado por 100 kg ou fixo por CT-e | varia | Simfrete 2026 |
| TDE (dificuldade de entrega) | % do frete | a partir de 20%, mínimo de R$ 20 | [Intelipost, 2018](https://www.intelipost.com.br/blog/taxa-de-frete-como-calcular/); [Senior](https://www.senior.com.br/blog/taxas-de-transporte-de-carga-e-mercadorias) |
| TRT (restrição de trânsito) | % do frete | até 15% a 20% | Senior; Intelipost |
| TDA (difícil acesso) | % do frete, com mínimo e máximo | varia | [TOTVS](https://tdn.totvs.com/pages/releaseview.action?pageId=518482476) |
| ICMS sobre o frete | entra no preço | 12% ou 7% interestadual; 18% é a alíquota geral interna de MG | [Contmatic 2026](https://simplifique.contmatic.com.br/blogs/tabela-icms-2026) |

**TDE nas prefeituras:** a TDE costuma ser cobrada quando o recebimento é demorado, com fila, ordem de chegada ou horário restrito, situação comum em almoxarifado público. Pergunte sempre se a cotação inclui TDE.

### Cotações simuladas: Jadlog (único simulador público que funcionou)

Condições:
- **Onde e quando:** simulador público em [jadlog.com.br/siteInstitucional/simulacao.jad](https://www.jadlog.com.br/siteInstitucional/simulacao.jad), em 18/10/2026, das 02:50 às 03:07 (horário de Brasília).
- **Parâmetros:** origem CEP 38061-080 (Uberaba), entrega em domicílio, sem dimensões, valor da nota de R$ 68/kg.
- **De onde vem o valor da nota:** é o preço típico do café nas licitações do Monitor (`data.json` de 17/10/2026).

O site avisa que o valor "é estimado e está sujeito à confirmação... de taxas, tarifas, cubagem para sua região e impostos".

**Valor total do frete, em R$ (modalidade Rodo; Econômico entre parênteses):**

| Destino (km por estrada) | 100 kg | 500 kg | 1.000 kg |
|---|---|---|---|
| Belo Horizonte-MG (480) | 696 (644) | 2.794 (2.803) | 5.207 (5.503) |
| São Paulo-SP (478) | 595 (577) | 2.367 (2.488) | 4.380 (4.876) |
| Goiânia-GO (458) | 552 (636) | 2.157 (2.570) | 3.955 (4.987) |
| Curitiba-PR (861) | 567 (522) | 2.168 (2.226) | 4.031 (4.355) |
| Recife-PE (2.312) | 792 (1.068) | 3.368 (4.750) | 6.263 (9.351) |
| Manaus-AM (3.485) | 1.428 (1.079) | 6.581 (4.793) | 13.021 (9.435) |

**Em R$ por kg (Rodo):** de R$ 5,52 a R$ 7,92 por kg com 100 kg, e de R$ 3,96 a R$ 6,26 por kg com 1.000 kg, fora Manaus (R$ 14,28 e R$ 13,02 por kg).

O mesmo simulador, com 100 kg, também deu valores para a modalidade **Package**: BH 1.517, SP 1.079, Goiânia 1.395, Curitiba 1.662, Recife 2.703 e Manaus 4.423. Não serve para esse volume.

**O que muda com o valor da nota:** simulamos cada rota com nota de R$ 0 e de R$ 10.000.
- **Capitais SP, BH e Recife:** o frete sobe de 2,1% a 2,4% do valor da nota.
- **Curitiba e Manaus:** sobe cerca de 1,1%.
- **Goiânia e interior:** sobe de 0,70% a 0,80%.
- **Mediana:** 0,8%. Para café a R$ 68/kg, isso dá de R$ 0,48 a R$ 1,64 por kg só desta parte.

**Interior × capital (Rodo, nota de R$ 0, 1.000 kg):**

| Destino (km) | Frete 1.000 kg | R$/kg |
|---|---|---|
| Ribeirão Preto-SP (171) | 3.041 | 3,04 |
| Pitangui-MG (393) | 4.058 | 4,06 |
| Bocaiúva-MG (690) | 4.058 | 4,06 |
| Guanambi-BA (1.023) | 4.573 | 4,57 |
| Seberi-RS (1.335) | 4.191 | 4,19 |
| Pesqueira-PE (2.109) | 9.377 | 9,38 |
| Jaguaribe-CE (2.517) | 9.766 | 9,77 |
| Recife-PE, capital (2.312) | 4.803 | 4,80 |

O que esta tabela mostra:
- **A Jadlog cobra por região/CEP, não por km exato.** Pitangui e Bocaiúva pagam o mesmo, mesmo com 300 km de diferença na estrada.
- **O interior do Nordeste custa perto do dobro da capital.**
- **Sobre os CEPs:** fomos nós que escolhemos os CEPs do interior (por exemplo, 35650-000 para Pitangui). Eles existem na base dos Correios, mas o simulador não mostra o nome da cidade.

**Pacotes leves (Rodo, nota de R$ 68/kg):** 10 kg custaram R$ 64 (SP), R$ 60 (Goiânia) e R$ 86 (Recife). Com 50 kg e nota de R$ 0, os valores ficaram entre R$ 236 e R$ 339 nas capitais, fora Manaus (R$ 684). Com 2.000 kg para SP, R$ 8.528, e com 5.000 kg, R$ 20.026 (R$ 4,00 a R$ 4,26 por kg). Ou seja, acima de 1.000 kg o fracionado não fica mais barato por kg.

### Correios (balcão, sem contrato)

Calculador público em [www2.correios.com.br/sistemas/precosPrazos](https://www2.correios.com.br/sistemas/precosPrazos/), em 18/10/2026, das 02:56 às 02:57 (horário de Brasília). Origem CEP 38061-080, caixa de 40 × 40 × 50 cm, sem valor declarado. O limite é de 30 kg por caixa. O último reajuste de encomendas foi em 12/04/2026, pelo IPCA de 4,26% ([SuperFrete](https://superfrete.com/blog/reajuste-precos-correios)).

| Destino | PAC 10 kg | PAC 30 kg | SEDEX 10 kg | SEDEX 30 kg | Prazo PAC |
|---|---|---|---|---|---|
| Belo Horizonte | 86,40 | 203,20 | 103,00 | 243,80 | 5 dias úteis |
| São Paulo | 166,10 | 391,70 | 293,70 | 688,90 | 5 dias úteis |
| Goiânia | 185,60 | 435,20 | 362,90 | 849,30 | 7 dias úteis |
| Curitiba | 185,60 | 435,20 | 362,90 | 849,30 | 7 dias úteis |
| Recife | 295,80 | 692,60 | 549,10 | 1.280,30 | 8 dias úteis |
| Manaus | 345,90 | 808,30 | 672,20 | 1.568,20 | 19 dias úteis |

O PAC de 30 kg sai entre R$ 6,77 e R$ 26,94 por kg, bem mais caro por kg que a Jadlog com 50 kg ou mais. Os Correios servem para **amostras** (muitas licitações pedem) e para entregas de até cerca de 30 kg.

### Transportadoras que não conseguimos simular

| Transportadora | Motivo |
|---|---|
| Braspress | a cotação online exige cadastro com CNPJ e passa por reCAPTCHA ([página](https://www.braspress.com/acesso-rapido/cotacao-online/)) |
| Patrus | só tem formulário de contato, sem preço na hora ([página](https://www.patrus.com.br/contato/cotacao-de-frete/)) |
| Rodonaves | a cotação fica em um aplicativo com login |
| Jamef | a página de cotação não carregou conteúdo sem login |
| TNT/FedEx | o site não abriu pelo nosso acesso (erro 502) |
| Total Express | o site recusou a conexão (erro 400) |

Não encontramos tabelas públicas atuais dessas empresas. Para calibrar a fórmula com elas, o dono precisa pedir cotação com o CNPJ da torrefação.

## 3. Fretes de referência do setor de café

- **Frete de café por saca:** não encontramos valor atual (2026) em Notícias Agrícolas, CEPEA, Cooxupé ou Cecafé. As buscas trouxeram só o preço da saca. Também não encontramos tabela pública de frete por saca dessas fontes.
- **SIFRECA (ESALQ-LOG), período de 31/08 a 04/10/2026:** a tabela aberta em [sifreca.esalq.usp.br](https://sifreca.esalq.usp.br) traz 100 rotas de algodão, farelo de soja, trigo, álcool, açúcar, milho, gesso, soja e fertilizantes. **Não há café.** "Outros produtos" fica na área de assinante.
  - **Medianas em R$ por tonelada por km:** todas as rotas 0,2854; algodão em fardos 0,2762; gesso 0,2498; soja 0,2835.
  - **Rotas com origem em Uberaba (gesso):** Sacramento-MG, R$ 74,00/t (0,9487/t.km); Prata-MG, R$ 80,00/t; Itumbiara-GO, R$ 113,56/t; Unaí-MG, R$ 150,00/t (0,2370/t.km); Alto Garças-MT, R$ 204,60/t.
  - **Conta nossa, não é cotação:** para carga agrícola em caminhão cheio de 25 a 37 t, R$ 0,28/t.km dá cerca de **R$ 0,028 por kg a cada 100 km**, ou R$ 8,30 por saca de 60 kg em 500 km. Isso é de 10 a 100 vezes mais barato por kg que o fracionado de 100 a 1.000 kg. A diferença mostra o peso do custo fixo de cada envio pequeno.

## 4. Frota própria (utilitário ou VUC)

Dados encontrados:
- **Diesel S10:** R$ 7,36/L, preço médio na semana de 04 a 10/10/2026 ([ANP, síntese 41/2026](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arq-sintese-semanal/2026/sintese-precos-41.pdf)).
- **VUC** ([guia de 26/08/2026](https://blog.caminhoesecarretas.com.br/2026/08/caminhao-vuc-guia/)):
  - consumo de 5 a 8 km/L (7 a 8 na estrada);
  - manutenção de R$ 8.000 a R$ 15.000 por ano e seguro de R$ 6.000 a R$ 14.000 por ano;
  - jogo de 6 pneus de R$ 3.600 a R$ 7.200, trocado a cada 50 a 70 mil km;
  - preço novo de R$ 195.000 a R$ 320.000, mais o baú (R$ 15.000 a R$ 40.000);
  - carga de 1.800 kg (Iveco Daily 35S14) a 5.800 kg (VW Delivery 9.170).
- **Motorista:** salário mediano de admissão em MG de R$ 2.761 ([Numerando/Novo CAGED, março de 2026](https://numerando.com.br/salarios/motorista-de-caminhao/minas-gerais)). O custo para a empresa fica entre 1,5 e 1,7 vez o salário no Simples ([Contabilidade Zen, 2026](https://www.contabilidadezen.com.br/blog/quanto-custa-funcionario-encargos-2026/)), ou seja, de R$ 4.140 a R$ 4.690 por mês.
- **Pedágio, exemplo:** as 4 praças da Bandeirantes entre Limeira e Caieiras somam R$ 51,30 para carro desde 01/07/2026 ([Motiva Autoban](https://rodovias.motiva.com.br/autoban/noticias/2026/junho/novas-tarifas-de-pedagio-entram-em-vigor-no-dia-1--de-julho/)). Para caminhão, multiplica-se pelo número de eixos ([Emsampa](https://www.emsampa.com.br/rotas_rodoviarias_V/uberaba_barueri.htm)): R$ 102,60 só nesse trecho, para 2 eixos. A rota Uberaba-SP tem 12 praças.
- **Reajuste do setor:** o custo do fracionado (INCT-F, NTC&Logística) subiu 8,19% em 12 meses e o da lotação, 8,36% ([Agência iNFRA, 28/08/2026](https://agenciainfra.com/blog/?p=46649)).

Contas nossas com esses números:
- **Só o combustível do VUC:** R$ 7,36 ÷ 7 km/L = **cerca de R$ 1,05 por km**.
- **Somando pneus e manutenção:** com uma premissa nossa de 40 mil km por ano, o custo variável fica em cerca de R$ 1,30 a R$ 1,60 por km, ainda sem motorista, seguro, depreciação e pedágio.
- **Custo completo:** não achamos estudo atual da NTC ou da CNT com R$/km de VUC. Como aproximação, usamos o CCD da ANTT para 2 eixos (R$ 4,07 por km), porque o piso foi montado sobre custos de rodar (combustível, pneus, manutenção, motorista, capital). Como o caminhão próprio volta vazio, conte **ida e volta**.
- **Comparação:** com essa aproximação, a frota própria só compensa perto de casa (Triângulo Mineiro, até umas poucas centenas de km) ou quando a mesma viagem atende várias prefeituras.

## 5. Fórmula proposta para o sistema

### Por entrega

```
FRACIONADO = 180 + kg × (2,10 + 0,23 × km/100) + 0,008 × valor_da_nota
LOTAÇÃO    = 451,84 + 4,0738 × km  (+ pedágio; piso ANTT 2 eixos, só ida)
custo_entrega = menor(FRACIONADO, LOTAÇÃO)
```

### Por licitação, com N entregas

```
kg_entrega = kg_total ÷ N
frete_total = N × custo_entrega(kg_entrega, km)
frete_por_kg = frete_total ÷ kg_total
```

### De onde vêm os parâmetros

- **F, A e B:** ajuste por mínimos quadrados sobre 42 cotações Jadlog Rodo com nota de R$ 0, de 100 a 1.000 kg e de 171 a 3.485 km, 13 destinos, simuladas em 18/10/2026.
- **Arredondamento:** F = R$ 180 por envio, A = R$ 2,10 por kg, B = R$ 0,23 por kg a cada 100 km. O erro médio é de 17%, praticamente sem viés (+1%).
- **0,8% do valor da nota:** é a mediana medida. Para SP, BH e Recife capital, use 2,4% se quiser ser prudente.
- **Mínimo por envio:** o próprio F (R$ 180). Abaixo de 30 kg, use os Correios.
- **Atualização:** reajuste F, A e B uma vez por ano pelo INCT-F. Troque o CC e o CCD quando a ANTT publicar nova portaria.

### Tabela de resultados

Valores em R$, com nota de R$ 68/kg e uma entrega. O piso de lotação é só ida e não inclui pedágio, lucro nem tributos.

| km | kg | Fracionado (R$) | R$/kg | Lotação 2 eixos, piso (R$) | R$/kg | Frota própria, ida e volta (R$) | Mais barato |
|---|---|---|---|---|---|---|---|
| 100 | 100 | 467 | 4,67 | 859 | 8,59 | 1.267 | fracionado |
| 100 | 500 | 1.617 | 3,23 | 859 | 1,72 | 1.267 | lotação |
| 100 | 1.000 | 3.054 | 3,05 | 859 | 0,86 | 1.267 | lotação |
| 300 | 100 | 513 | 5,13 | 1.674 | 16,74 | 2.896 | fracionado |
| 300 | 500 | 1.847 | 3,69 | 1.674 | 3,35 | 2.896 | lotação (por pouco) |
| 300 | 1.000 | 3.514 | 3,51 | 1.674 | 1,67 | 2.896 | lotação |
| 600 | 100 | 582 | 5,82 | 2.896 | 28,96 | 5.340 | fracionado |
| 600 | 500 | 2.192 | 4,38 | 2.896 | 5,79 | 5.340 | fracionado |
| 600 | 1.000 | 4.204 | 4,20 | 2.896 | 2,90 | 5.340 | lotação |
| 1.000 | 100 | 674 | 6,74 | 4.526 | 45,26 | 8.599 | fracionado |
| 1.000 | 500 | 2.652 | 5,30 | 4.526 | 9,05 | 8.599 | fracionado |
| 1.000 | 1.000 | 5.124 | 5,12 | 4.526 | 4,53 | 8.599 | lotação (por pouco) |
| 2.000 | 100 | 904 | 9,04 | 8.599 | 85,99 | 16.747 | fracionado |
| 2.000 | 500 | 3.802 | 7,60 | 8.599 | 17,20 | 16.747 | fracionado |
| 2.000 | 1.000 | 7.424 | 7,42 | 8.599 | 8,60 | 16.747 | fracionado |

### Quando compensa fracionado ou lotação

Peso a partir do qual o caminhão dedicado de 2 eixos fica mais barato, considerando o piso ANTT:

| Distância | Peso de equilíbrio por entrega |
|---|---|
| 100 km | ~240 kg |
| 300 km | ~450 kg |
| 600 km | ~680 kg |
| 1.000 km | ~880 kg |
| 2.000 km | ~1.160 kg |

O que isso significa:
- **Abaixo desses pesos:** fracionado.
- **Acima:** vale pedir cotação de lotação (caminhão só seu). Como o piso fica abaixo do preço de mercado, na prática o ponto de virada fica um pouco acima desses pesos.
- **De 1.000 a 5.000 kg:** quase sempre lotação, com VUC ou toco de 2 eixos (o VW Delivery 9.170 leva até 5.800 kg).
- **Região Norte:** o fracionado para Manaus custou R$ 12 a R$ 14 por kg. O modelo erra para menos ali (27% abaixo, em média).

### Exemplo de entrega parcelada (1.000 kg no total, nota de R$ 68/kg, fracionado)

| Distância | 1 entrega | 4 entregas de 250 kg | 12 entregas de 83 kg |
|---|---|---|---|
| 300 km | R$ 3.514 (3,51/kg) | R$ 4.054 (4,05/kg) | R$ 5.494 (5,49/kg) |
| 600 km | R$ 4.204 (4,20/kg) | R$ 4.744 (4,74/kg) | R$ 6.184 (6,18/kg) |
| 1.000 km | R$ 5.124 (5,12/kg) | R$ 5.664 (5,66/kg) | R$ 7.104 (7,10/kg) |

Cada entrega a mais acrescenta cerca de R$ 180 (o custo fixo do envio). Em licitações de entrega parcelada, o frete por kg pode ficar de 39% a 56% acima do de uma entrega só.

### Teste da fórmula contra as cotações reais (nota de R$ 68/kg)

| Destino | Fórmula × cotação, por peso |
|---|---|
| Goiânia | 0% a -6% |
| São Paulo | -7% a -13% |
| Belo Horizonte | -20% a -26% |
| Curitiba | +13% a +19% |
| Recife | +23% a +30% |
| Manaus | -13% a -17% |

Para uma margem prudente, some uma folga de 20% ao frete calculado, ou use a cotação real quando a licitação parecer boa.

## 6. Limitações e próximos passos

1. **Preço de balcão:** a calibração vem só da Jadlog, com preço de balcão. Com contrato (Braspress, Patrus, Rodonaves, Jamef), o preço pode ser menor, mas não há número público. O ideal é o dono pedir de 2 a 3 cotações com o CNPJ (100, 500 e 1.000 kg para SP, BH, Goiânia, Curitiba e Recife) e trocarmos F, A, B e o percentual da nota.
2. **Taxas que podem não estar na cotação:** a cotação Jadlog pode não incluir TDE ou agendamento, comuns em prefeituras.
3. **Peso cubado:** a Jadlog usa divisor 5.000, ou seja, 200 kg por m³ ([termos Jadlog](https://www.jadlog.com.br/jadlog/arquivos/TermoseCondicoes.pdf)). Café a vácuo em caixas deve pesar mais que isso por m³, e então vale o peso real. Confira com a caixa real (peso e medidas).
4. **Sacramento-MG** fica a 76 km de Uberaba. No fracionado, a transportadora costuma coletar na região, então a diferença tende a ser pequena. Não medimos isso.
5. **Frete de café por saca:** não encontramos referência atual. O SIFRECA de café só existe para assinante.

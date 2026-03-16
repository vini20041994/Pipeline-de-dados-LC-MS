# Cálculo do Top 5 utilizando a modelagem probabilística

Este arquivo aplica a modelagem mostrada no projeto:

\[
P(C_i \mid S_{frag}, S_{base}, S_{iso}) =
\frac{P(S_{frag}, S_{base}, S_{iso} \mid C_i) \cdot P(C_i)}{P(S_{frag}, S_{base}, S_{iso})}
\]

\[
Score_{final}(C_i) = w_1\hat{S}_{frag} + w_2\hat{S}_{base} + w_3\hat{S}_{iso}
\]

com pesos padrão:

- \(w_1 = 0.4\)
- \(w_2 = 0.4\)
- \(w_3 = 0.2\)

## Como foi calculado

1. Normalização min-max dos scores `fragmentation`, `base` e `isotope`.
2. Cálculo do `Score_final` por candidato.
3. Estimativa de prior \(P(C_i)\) a partir de `base_norm` no conjunto do sinal.
4. Estimativa de \(P(S_{frag}, S_{base}, S_{iso} | C_i)\) por produto:
   - `frag_norm * base_norm * iso_norm`.
5. Cálculo do posterior \(P(C_i | S_{frag}, S_{base}, S_{iso})\).
6. Ordenação por `Score_final` e truncamento `rank <= 5`.

## Exemplo calculado (Signal 458)

| Signal | Ranking | Molécula | Score final | Probabilidade posterior |
|---|---:|---|---:|---:|
| 458 | 1 | Quercetin | 1.000000 | 0.679342 |
| 458 | 2 | Myricetin | 0.746667 | 0.151053 |
| 458 | 3 | Luteolin | 0.676190 | 0.133690 |
| 458 | 4 | Kaempferol | 0.478095 | 0.033274 |
| 458 | 5 | Apigenin | 0.238095 | 0.002641 |

## Scripts

- Pipeline ETL (Pandas): `etl/score.py`
- Cálculo demonstrativo sem dependências externas: `examples/calculate_top5_no_deps.py`
